import feedparser
import pandas as pd
import os
import time
from urllib.parse import quote

from query_builder import build_queries

# ---------------------------------------------------------------------
# Search Queries
# ---------------------------------------------------------------------
# Built from species x conflict-event x region combinations instead of
# a flat hand-written list — see query_builder.py.
# ---------------------------------------------------------------------

QUERIES = build_queries()

YEARS = range(2020, 2027)

articles = []

print(f"Running {len(QUERIES)} targeted queries across {len(list(YEARS))} years "
      f"({len(QUERIES) * len(list(YEARS))} total requests).\n")

# ---------------------------------------------------------------------
# Google News RSS
# ---------------------------------------------------------------------

for year in YEARS:

    print(f"\n========== {year} ==========")

    for query in QUERIES:

        search = f"{query} {year}"

        rss_url = (
            "https://news.google.com/rss/search?"
            f"q={quote(search)}&hl=en-IN&gl=IN&ceid=IN:en"
        )

        feed = feedparser.parse(rss_url)

        print(f"{query:<55} -> {len(feed.entries)} headlines")

        for entry in feed.entries:

            articles.append({
                "year": year,
                "query": query,
                "source": entry.get("source", {}).get("title", "Unknown"),
                "title": entry.title,
                "url": entry.link,
                "date": entry.get("published", "")
            })

        time.sleep(0.2)

# ---------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------

df = pd.DataFrame(articles)

df = df.drop_duplicates(subset="url")

os.makedirs("../data/raw_articles", exist_ok=True)

output = "../data/raw_articles/articles_2020_2026.csv"

df.to_csv(output, index=False)

print("\n===============================")
print(f"Saved {len(df)} unique headlines.")
print(f"CSV: {output}")
print("===============================")
