"""
Resolves each article's real publisher URL (Google News RSS links are
encoded redirect tokens) and extracts just the clean article body text -
no navigation, ads, related-article links, or boilerplate.

WHY THE OLD VERSION FAILED FOR EVERY ROW
-----------------------------------------
The `googlenewsdecoder` package's decode functions (`new_decoderv1`,
`GoogleDecoder`, etc.) send their FIRST request - the one that fetches
the signature/timestamp needed to decode the URL - with NO custom
headers at all. Google reliably serves a stripped-down/consent page to
requests with the default python-requests user-agent, so that first
request almost always fails to find the expected page element, which
means decoding fails for every single URL, every time - not
intermittently, but systematically. That's why article_body ended up
empty for 100% of rows.

This version reimplements the same 3-step decode (get base64 token ->
fetch signature/timestamp -> call Google's batchexecute endpoint) but
sends a real browser User-Agent (and a shared session, so cookies from
step 1 carry into step 2) on every request. It also retries on
transient failures and reports exactly which step failed, instead of
silently returning "".

Primary body extraction: trafilatura. Falls back to newspaper3k if
trafilatura returns nothing usable.
"""

import json
import time
from urllib.parse import quote, urlparse

import requests
import trafilatura
from newspaper import Article

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/webp,*/*;q=0.8"
    ),
}

MIN_BODY_LENGTH = 200  # below this, treat extraction as a failure
REQUEST_TIMEOUT = 12
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2


def _get(session, url, timeout=REQUEST_TIMEOUT, retries=MAX_RETRIES):
    """GET with retries/backoff, always using the shared session+headers."""
    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = session.get(url, timeout=timeout, allow_redirects=True)
            if resp.status_code == 429 and attempt < retries:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            return resp
        except requests.exceptions.RequestException as e:
            last_exc = e
            if attempt < retries:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    if last_exc:
        raise last_exc
    return None


def _get_base64_str(source_url):
    url = urlparse(source_url)
    path = url.path.split("/")
    if (
        url.hostname == "news.google.com"
        and len(path) > 1
        and path[-2] in ("articles", "read")
    ):
        return {"status": True, "base64_str": path[-1]}
    return {"status": False, "message": "Not a Google News article URL."}


def _get_decoding_params(session, base64_str):
    """
    Fetches the signature+timestamp Google needs to decode the URL.
    Tries /articles/{token} first, falls back to /rss/articles/{token}.
    Crucially: uses `session` so browser headers + cookies are sent.
    """
    try:
        from selectolax.parser import HTMLParser
    except ImportError:
        HTMLParser = None

    candidate_urls = [
        f"https://news.google.com/articles/{base64_str}",
        f"https://news.google.com/rss/articles/{base64_str}",
    ]

    last_message = "Unknown failure."
    for url in candidate_urls:
        try:
            resp = _get(session, url)
            if resp is None or resp.status_code != 200:
                last_message = f"HTTP {resp.status_code if resp else 'no response'} for {url}"
                continue

            if HTMLParser is not None:
                parser = HTMLParser(resp.text)
                el = parser.css_first("c-wiz > div[jscontroller]")
                if el is None:
                    last_message = f"No jscontroller element found at {url}"
                    continue
                sig = el.attributes.get("data-n-a-sg")
                ts = el.attributes.get("data-n-a-ts")
            else:
                # crude fallback without selectolax
                import re
                sig_match = re.search(r'data-n-a-sg="([^"]+)"', resp.text)
                ts_match = re.search(r'data-n-a-ts="([^"]+)"', resp.text)
                sig = sig_match.group(1) if sig_match else None
                ts = ts_match.group(1) if ts_match else None

            if not sig or not ts:
                last_message = f"Missing signature/timestamp at {url}"
                continue

            return {"status": True, "signature": sig, "timestamp": ts, "base64_str": base64_str}

        except requests.exceptions.RequestException as e:
            last_message = f"Request error at {url}: {e}"
            continue

    return {"status": False, "message": last_message}


def _decode_url(session, signature, timestamp, base64_str):
    try:
        url = "https://news.google.com/_/DotsSplashUi/data/batchexecute"
        payload = [
            "Fbv4je",
            f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,'
            f'null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
            f'"{base64_str}",{timestamp},"{signature}"]',
        ]
        post_headers = dict(HEADERS)
        post_headers["Content-Type"] = "application/x-www-form-urlencoded;charset=UTF-8"

        resp = session.post(
            url,
            headers=post_headers,
            data=f"f.req={quote(json.dumps([[payload]]))}",
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

        parsed = json.loads(resp.text.split("\n\n")[1])[:-2]
        decoded_url = json.loads(parsed[0][2])[1]
        return {"status": True, "decoded_url": decoded_url}

    except Exception as e:
        return {"status": False, "message": f"Error decoding batchexecute response: {e}"}


def resolve_final_url(url, verbose=False, session=None):
    """
    Given a Google News RSS link, returns (real_url, status_note).
    status_note explains what happened, for diagnostics.
    """
    if "news.google.com" not in url:
        return url, "not_a_google_news_url"

    if session is None:
        session = requests.Session()
        session.headers.update(HEADERS)

    b64 = _get_base64_str(url)
    if not b64["status"]:
        if verbose:
            print("   [decode] base64 extraction failed:", b64["message"])
        return url, f"decode_failed:{b64['message']}"

    params = _get_decoding_params(session, b64["base64_str"])
    if not params["status"]:
        if verbose:
            print("   [decode] params fetch failed:", params["message"])
        # Fallback: plain redirect-follow with proper headers (works for
        # a subset of links that still 302 normally).
        try:
            resp = _get(session, url)
            if resp is not None and resp.url and "news.google.com" not in resp.url:
                return resp.url, "resolved_via_redirect_fallback"
        except requests.exceptions.RequestException:
            pass
        return url, f"decode_failed:{params['message']}"

    decoded = _decode_url(session, params["signature"], params["timestamp"], b64["base64_str"])
    if not decoded["status"]:
        if verbose:
            print("   [decode] batchexecute decode failed:", decoded["message"])
        return url, f"decode_failed:{decoded['message']}"

    return decoded["decoded_url"], "resolved_via_decode"


def _fetch_html(session, url):
    """
    Fetch the final article page ourselves, using the same browser-headers
    session that already worked for the decode step. This is the key fix:
    trafilatura.fetch_url() and newspaper's Article.download() each make
    their OWN fresh request with a non-browser default user-agent, which
    many publishers (NDTV included) quietly block or serve a stripped page
    to. Fetching once here and handing the HTML to both extractors avoids
    that entirely.
    """
    try:
        resp = _get(session, url)
        if resp is None or resp.status_code != 200 or not resp.text:
            return None
        return resp.text
    except requests.exceptions.RequestException:
        return None


def extract_body_trafilatura(html, url=None):
    if not html:
        return ""
    try:
        text = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=False,
            include_links=False,
            favor_precision=True,
        )
        return text or ""
    except Exception:
        return ""


def extract_body_newspaper(html, url):
    if not html:
        return ""
    try:
        article = Article(url)
        article.set_html(html)
        article.parse()
        return article.text or ""
    except Exception:
        return ""


def get_article_body(url, resolve_redirect=True, sleep=0.3, verbose=False):
    """
    Given a (possibly Google News redirect) URL, returns
    (body_text, status_note). body_text is "" if extraction failed;
    status_note always explains why, for logging/diagnostics.
    """
    if not url:
        return "", "no_url"

    session = requests.Session()
    session.headers.update(HEADERS)

    if resolve_redirect:
        real_url, resolve_status = resolve_final_url(url, verbose=verbose, session=session)
    else:
        real_url, resolve_status = url, "resolve_skipped"

    html = _fetch_html(session, real_url)
    if html is None:
        time.sleep(sleep)
        return "", f"extraction_failed(page_fetch_failed after {resolve_status})"

    body = extract_body_trafilatura(html, real_url)
    method = "trafilatura"

    if len(body.strip()) < MIN_BODY_LENGTH:
        fallback = extract_body_newspaper(html, real_url)
        if len(fallback.strip()) > len(body.strip()):
            body = fallback
            method = "newspaper3k"

    time.sleep(sleep)

    body = body.strip()
    if len(body) < MIN_BODY_LENGTH:
        return "", f"extraction_failed(after {resolve_status})"

    return body, f"success({method}, {resolve_status}, {len(body)} chars)"


if __name__ == "__main__":
    # Quick manual diagnostic. Run this file directly on your own machine
    # (needs real internet access) to see exactly where things break:
    #   cd extractor && python body_extractor.py
    import pandas as pd

    try:
        df = pd.read_csv("../data/raw_articles/articles_2020_2026.csv")
        sample_urls = df["url"].dropna().head(5).tolist()
    except Exception:
        sample_urls = []

    if not sample_urls:
        print("Could not load sample URLs from ../data/raw_articles/articles_2020_2026.csv")
    else:
        for u in sample_urls:
            print("\nURL:", u[:90], "...")
            body, status = get_article_body(u, verbose=True)
            print("STATUS:", status)
            print("BODY PREVIEW:", body[:200] if body else "(empty)")