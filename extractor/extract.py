import json
import os
import time
import re

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from prompt import EXTRACTION_PROMPT
from body_extractor import get_article_body

# ==================================================
# Setup OpenAI
# ==================================================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==================================================
# Load Google News RSS Headlines
# ==================================================
articles = pd.read_csv("../data/raw_articles/articles_2020_2026.csv")

articles["title"] = articles["title"].fillna("").astype(str)
articles["source"] = articles["source"].fillna("").astype(str)
articles["date"] = articles["date"].fillna("").astype(str)
articles["url"] = articles["url"].fillna("").astype(str)

# ==================================================
# Filter likely conflict headlines
# ==================================================
ACTION_WORDS = [
    "attack", "attacked",
    "injured", "injury",
    "killed", "kills", "kill",
    "mauled", "mauls",
    "dead", "death",
    "livestock", "sheep", "goat", "cow", "yak", "poultry",
    "crop raiding", "crop damage", "tramples", "menace",
    "villager", "farmer", "herder", "shepherd"
]

SPECIES_WORDS = [
    "snow leopard",
    "leopard",
    "tiger",
    "bear",
    "wolf",
    "wild boar",
    "boar",
    "macaque",
    "monkey",
    "langur",
    "elephant",
    "nilgai",
    "blue bull",
    "sambar",
    "porcupine",
    "jackal",
]

EXCLUDE_WORDS = [
    "survey", "population", "tourism", "conservation",
    "habitat", "study", "research", "festival",
    "homestay", "density", "thriving", "allies",
    "ecotourism", "protect", "camera trap",
    "photography", "documentary", "climate change"
]

# Used only as a pre-filter signal for logging/QA; the LLM (per prompt.py
# Rule 8) is the source of truth for report_type on each incident it returns.
CUMULATIVE_PHRASES = [
    "this year", "so far", "till date", "to date",
    "this month", "this season", "this week",
    "and counting", "over the past", "in the last",
    "so far this",
]

CASUALTY_NUMBER_PATTERN = re.compile(
    r"\d+\s*(?:killed|kills|dead|deaths|injured|hurt|mauled|wounded)",
    re.IGNORECASE
)


def looks_cumulative(headline: str) -> bool:
    """Heuristic pre-check used only for QA logging - the LLM's own
    report_type field (see prompt.py Rule 8) is what actually gets saved."""
    text = (headline or "").lower()
    has_cumulative_phrase = any(phrase in text for phrase in CUMULATIVE_PHRASES)
    if not has_cumulative_phrase:
        return False
    if len(CASUALTY_NUMBER_PATTERN.findall(text)) >= 2:
        return True
    if "and counting" in text and CASUALTY_NUMBER_PATTERN.search(text):
        return True
    return False


articles["combined"] = articles["title"].str.lower()

articles = articles[
    articles["combined"].apply(
        lambda text:
            any(a in text for a in ACTION_WORDS)
            and any(s in text for s in SPECIES_WORDS)
            and not any(e in text for e in EXCLUDE_WORDS)
    )
]

# Remove duplicate headlines
articles = articles.drop_duplicates(subset="title").reset_index(drop=True)

print(f"Found {len(articles)} candidate conflict headlines.")
print(f"Processing {len(articles)} headlines...\n")

# ==================================================
# GPT Classification + Field Extraction (Batch Mode)
# ==================================================
BATCH_SIZE = 20
records = []

VALID_CONFLICT_TYPES = {
    "Human Injury", "Human Death", "Livestock Attack",
    "Crop Raiding", "Retaliation Against Wildlife",
}
VALID_REPORT_TYPES = {"single_incident", "aggregate_period_total"}

for start in range(0, len(articles), BATCH_SIZE):

    batch = articles.iloc[start:start + BATCH_SIZE]

    print(
        f"Batch {start//BATCH_SIZE + 1} "
        f"({start + 1}-{start + len(batch)})"
    )

    headlines = [
        {
            "headline": row.title,
            "date": row.date,
            "source": row.source,
            "url": row.url
        }
        for row in batch.itertuples(index=False)
    ]

    prompt = f"""
{EXTRACTION_PROMPT}

HEADLINES:
{json.dumps(headlines, indent=2)}
"""

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt
        )

        result = (
            response.output_text
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        data = json.loads(result)
        incidents = data.get("incidents", [])

        print(f"   incidents extracted: {len(incidents)}")

        # --------------------------------------------------
        # Attach original metadata back to each incident
        # --------------------------------------------------
        headline_lookup = {
            item["headline"]: item for item in headlines
        }

        for incident in incidents:

            headline = incident.get("headline", "")

            # If GPT didn't return headline, try summary
            if headline == "":
                headline = incident.get("summary", "")

            # Match against original batch
            if headline in headline_lookup:
                meta = headline_lookup[headline]
            else:
                # Fallback: fuzzy match using first matching title
                meta = next(
                    (
                        h for h in headlines
                        if h["headline"].lower().startswith(headline.lower()[:25])
                    ),
                    headlines[0]
                )

            # --------------------------------------------------
            # Validate + normalize fields the model returned.
            # We keep every row (never silently drop for a schema
            # mismatch) but flag anything odd via needs_review, so
            # nothing vanishes without a trace in incidents.csv.
            # --------------------------------------------------
            needs_review = []

            conflict_type = incident.get("conflict_type", "")
            if conflict_type not in VALID_CONFLICT_TYPES:
                needs_review.append(f"unrecognized_conflict_type:{conflict_type}")

            report_type = incident.get("report_type", "")
            if report_type not in VALID_REPORT_TYPES:
                # Model omitted it or used a wrong value - fall back to the
                # local heuristic rather than losing the distinction entirely.
                report_type = (
                    "aggregate_period_total"
                    if looks_cumulative(meta["headline"])
                    else "single_incident"
                )
                needs_review.append("report_type_backfilled_by_heuristic")

            if looks_cumulative(meta["headline"]) and report_type == "single_incident":
                needs_review.append("heuristic_flagged_possible_aggregate")

            incident["report_type"] = report_type
            incident["needs_review"] = "; ".join(needs_review)

            incident["headline"] = meta["headline"]
            incident["source"] = meta["source"]
            incident["url"] = meta["url"]

            records.append(incident)

        time.sleep(0.4)

    except Exception as e:
        print("   x Batch skipped:", e)

# ==================================================
# Build incidents DataFrame
# ==================================================
os.makedirs("../data/processed", exist_ok=True)

incidents = pd.DataFrame(records)

# Ensure required columns exist
required_columns = [
    "incident_date",
    "state",
    "district",
    "village",
    "species",
    "conflict_type",
    "livestock_killed",
    "human_injured",
    "human_dead",
    "summary",
    "confidence",
    "headline",
    "source",
    "url",
    "article_body",
    "report_type",
    "needs_review",
    "body_status",
]

for col in required_columns:
    if col not in incidents.columns:
        incidents[col] = ""

# Remove duplicate headlines
incidents = incidents.drop_duplicates(subset="headline").reset_index(drop=True)

# ==================================================
# Article Body Extraction
# ==================================================
# Fetched only for confirmed incidents, to avoid wasting requests on
# headlines that turned out irrelevant. Every row gets a body_status so
# failures are visible in the CSV instead of showing up as a silent blank.
# ==================================================
print(f"\nExtracting article bodies for {len(incidents)} confirmed incidents...\n")

bodies = []
body_statuses = []
success_count = 0

for i, row in incidents.iterrows():
    url = row["url"]
    print(f"[{i + 1}/{len(incidents)}] {row['headline'][:70]}")

    if not url:
        bodies.append("")
        body_statuses.append("no_url")
        continue

    try:
        body, status = get_article_body(url)
    except Exception as e:
        body, status = "", f"exception:{e}"

    if body:
        success_count += 1
    else:
        print(f"      -> body extraction failed: {status}")

    bodies.append(body)
    body_statuses.append(status)

incidents["article_body"] = bodies
incidents["body_status"] = body_statuses

print(
    f"\nBody extraction succeeded for {success_count}/{len(incidents)} incidents "
    f"({success_count / len(incidents) * 100:.0f}%)."
    if len(incidents) else "\nNo incidents to extract bodies for."
)
if len(incidents) and success_count == 0:
    print(
        "WARNING: 0 bodies extracted. This usually means either (a) your\n"
        "machine has no internet access from this process, or (b) Google is\n"
        "blocking the decode requests outright. Run "
        "`python body_extractor.py` directly for a step-by-step diagnostic\n"
        "against a few real URLs from your own dataset."
    )

# ==================================================
# Save Results
# ==================================================
output_path = "../data/processed/incidents.csv"
incidents.to_csv(output_path, index=False)

n_single = (incidents["report_type"] == "single_incident").sum()
n_aggregate = (incidents["report_type"] == "aggregate_period_total").sum()
n_flagged = (incidents["needs_review"] != "").sum()

print("\n===================================")
print(f"Extracted {len(incidents)} incidents.")
print(f"   - {n_single} single-incident reports")
print(f"   - {n_aggregate} aggregate/period-total reports (tagged - see report_type column)")
print(f"   - {n_flagged} rows flagged for review (see needs_review column)")
print(f"Saved to {output_path}")
print("===================================")
