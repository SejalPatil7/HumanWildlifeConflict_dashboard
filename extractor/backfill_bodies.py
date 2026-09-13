"""
Backfills article_body text onto an ALREADY-EXTRACTED incidents.csv,
without re-running the LLM classification step in extract.py.

Reads:  ../data/processed/incidents.csv
Writes: ../data/processed/incidents_with_bodies.csv   (new file, original untouched)

Why this exists separately from extract.py:
- extract.py re-does GPT classification every time it runs (costs API calls).
- If your incidents.csv is already correct and only article_body is empty
  (e.g. it was generated on a machine/sandbox without real internet access),
  you just need this script to go fetch the bodies.

Safe to re-run: it skips rows that already have a non-empty article_body,
so you can stop/restart without redoing work or re-hitting URLs that
already succeeded.

Run from the extractor/ folder:
    cd extractor
    python backfill_bodies.py
"""

import pandas as pd
from body_extractor import get_article_body

INPUT_PATH = "../data/processed/incidents.csv"
OUTPUT_PATH = "../data/processed/incidents_with_bodies.csv"

SAVE_EVERY = 10  # write progress to disk every N rows, in case of a crash/interrupt


def main():
    # Resume support: if the output file already exists from a previous
    # partial run, continue from that instead of starting over.
    try:
        df = pd.read_csv(OUTPUT_PATH)
        print(f"Resuming from existing {OUTPUT_PATH} ({len(df)} rows).")
    except FileNotFoundError:
        df = pd.read_csv(INPUT_PATH)
        print(f"Starting fresh from {INPUT_PATH} ({len(df)} rows).")

    if "article_body" not in df.columns:
        df["article_body"] = ""
    if "body_status" not in df.columns:
        df["body_status"] = ""

    df["article_body"] = df["article_body"].fillna("").astype(str)
    df["url"] = df["url"].fillna("").astype(str)

    todo_mask = df["article_body"].str.len() == 0
    total_todo = todo_mask.sum()
    print(f"{total_todo} rows still need a body ({len(df) - total_todo} already done).\n")

    success_count = 0
    processed = 0

    for i in df.index[todo_mask]:
        url = df.at[i, "url"]
        headline = str(df.at[i, "headline"])[:70] if "headline" in df.columns else url[:70]
        processed += 1
        print(f"[{processed}/{total_todo}] {headline}")

        if not url:
            df.at[i, "article_body"] = ""
            df.at[i, "body_status"] = "no_url"
            continue

        try:
            body, status = get_article_body(url)
        except Exception as e:
            body, status = "", f"exception:{e}"

        df.at[i, "article_body"] = body
        df.at[i, "body_status"] = status

        if body:
            success_count += 1
        else:
            print(f"      -> failed: {status}")

        if processed % SAVE_EVERY == 0:
            df.to_csv(OUTPUT_PATH, index=False)
            print(f"      (progress saved: {processed}/{total_todo})")

    df.to_csv(OUTPUT_PATH, index=False)

    print("\n===================================")
    print(f"Attempted {total_todo} rows this run.")
    print(f"Succeeded: {success_count}/{total_todo}" if total_todo else "Nothing to do.")
    print(f"Saved to {OUTPUT_PATH}")
    print("===================================")

    if total_todo and success_count == 0:
        print(
            "\nWARNING: 0 bodies extracted. Run `python body_extractor.py`\n"
            "directly for a step-by-step diagnostic against a few real URLs\n"
            "from your dataset - this usually means either no real internet\n"
            "access from this machine, or Google blocking the decode requests."
        )


if __name__ == "__main__":
    main()