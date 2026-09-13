"""
Resolves Google News redirect URLs (news.google.com/rss/articles/...) into
the real publisher article URL, and writes the result back into
data/processed/incidents.csv.

Run this once after extraction, before the dashboard reads the CSV -
the dashboard itself never needs to do this resolving.

Usage:
    cd extractor
    python resolve_urls.py
"""

import time
import pandas as pd
import requests

INCIDENTS_PATH = "../data/processed/incidents.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def resolve_google_news_url(url, timeout=8):
    if not isinstance(url, str) or "news.google.com" not in url:
        return url

    try:
        resp = requests.get(
            url, headers=HEADERS, timeout=timeout, allow_redirects=True
        )
        final_url = resp.url
        if "news.google.com" in final_url:
            return url
        return final_url
    except requests.RequestException:
        return url


def main():
    df = pd.read_csv(INCIDENTS_PATH)

    if "url" not in df.columns:
        print("No 'url' column found - nothing to resolve.")
        return

    total = len(df)
    resolved = []

    print(f"Resolving {total} URLs (this can take a while - one request per link)...")

    for i, url in enumerate(df["url"], start=1):
        resolved.append(resolve_google_news_url(url))
        if i % 25 == 0 or i == total:
            print(f"  {i}/{total} done")
        time.sleep(0.3)

    df["url"] = resolved
    df.to_csv(INCIDENTS_PATH, index=False)

    n_still_google = sum("news.google.com" in u for u in resolved if isinstance(u, str))
    print("\n===============================")
    print(f"Done. {total - n_still_google}/{total} resolved to publisher URLs.")
    print(f"{n_still_google} could not be resolved and kept their original link.")
    print(f"Saved back to: {INCIDENTS_PATH}")
    print("===============================")


if __name__ == "__main__":
    main()