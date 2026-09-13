EXTRACTION_PROMPT = """
You extract structured human-wildlife conflict incidents from Himalayan news HEADLINES.

Return ONLY valid JSON in this format:

{
  "incidents": [
    {
      "headline": "Snow leopard kills 37 sheep and Pashmina goats in Ladakh",
      "incident_date": "2024-10-14",
      "state": "Ladakh",
      "district": "",
      "species": "Snow Leopard",
      "conflict_type": "Livestock Attack",
      "livestock_killed": 37,
      "human_injured": 0,
      "human_dead": 0,
      "summary": "Snow leopard killed livestock in Ladakh.",
      "confidence": 0.98,
      "report_type": "single_incident"
    }
  ]
}

GENERAL RULES

1. Use ONLY information explicitly present in the headline and publication date.
2. Do NOT infer district, village, livestock counts, or casualties if they are
   not mentioned. Leave district/village as "" if not stated. Never guess a
   state from a district or town name unless the state itself is explicitly
   named or unambiguous from context in the headline.
3. Classify conflict_type as exactly one of:
   - Human Injury
   - Human Death
   - Livestock Attack
   - Crop Raiding
   - Retaliation Against Wildlife
   Retaliation Against Wildlife means an animal was killed, beaten, poisoned,
   or captured by humans/villagers in response to conflict — use this even if
   the same headline also mentions an earlier human death or livestock loss,
   as long as the retaliation against the ANIMAL is the main reported event.
   Do not classify a headline as Human Death or Human Injury solely because
   an animal died or was killed — that is about the animal, not a human
   casualty.
4. Species must be normalized to one of these exact names:
   Snow Leopard, Leopard, Tiger, Himalayan Brown Bear, Asiatic Black Bear,
   Wolf, Wild Boar, Rhesus Macaque, Common Langur, Asian Elephant, Nilgai,
   Sambar Deer, Porcupine, Golden Jackal.
   - If the headline just says "bear" with no species detail, use
     "Asiatic Black Bear" for Kashmir/Jammu/Himachal Pradesh incidents and
     "Himalayan Brown Bear" for Ladakh/high-altitude incidents; if truly
     ambiguous, use "Asiatic Black Bear".
   - If the headline just says "monkey", use "Rhesus Macaque".
   - If a headline explicitly says the animal was misidentified (e.g. "tiger,
     not leopard, killed..."), use the CORRECTED species stated in the
     headline, not the originally assumed one.
   - If the animal named genuinely does not match any of the above (a
     species not on this list at all), still extract the incident but set
     species to the animal's plain common name exactly as named in the
     headline (capitalized), and set "confidence" to 0.5 or lower. Do NOT
     force-fit it into an unrelated category on this list, and do NOT invent
     a species that was not named in the headline.
5. Ignore conservation, tourism, surveys, research, population estimates,
   habitat stories, photography, and awareness articles.
6. GEOGRAPHIC SCOPE: this dataset covers the Indian Himalayan Region only —
   Jammu & Kashmir, Ladakh, Himachal Pradesh, Uttarakhand, Sikkim, Darjeeling
   hills (West Bengal), and Arunachal Pradesh. If a headline is clearly about
   a location OUTSIDE this scope (a different Indian state such as
   Rajasthan, Maharashtra, Uttar Pradesh plains cities, Delhi, etc., or
   about Pakistan / Azad Kashmir / Khyber Pakhtunkhwa / any other country),
   return no incident for it: {"incidents":[]} for that headline. If the
   headline gives no location information at all, still extract it with
   state "" — do not reject solely for a missing location.

If a headline is not describing a human-wildlife conflict incident, return
no incident for it (it should simply not appear in the "incidents" array).

NUMBER-TO-FIELD MAPPING (apply strictly, in order, for every number in the headline)

7. Identify what each number refers to using the words immediately attached
   to it. Do NOT assume a number belongs to livestock unless livestock-
   specific words are present.
   - Human victims: person, people, man, woman, boy, girl, villager,
     shepherd, herder, child, resident, farmer, tourist, student, labourer,
     or "X killed"/"X dead"/"X injured" with no animal/livestock noun
     attached.
   - Livestock victims: sheep, goat, Pashmina goat, cattle, cow, ox, yak,
     horse, mule, poultry, hen, livestock, or animals explicitly described
     as belonging to a herd/farm.
   - If a number has no explicit subject stated, but the headline is about
     an attack on people/a place (not a herd/farm), default that number to
     HUMAN casualties, not livestock. Only put a number in livestock_killed
     if livestock words are explicitly present.
   - Map "killed"/"dead"/"deaths" -> human_dead (or livestock_killed if
     livestock words are present). Map "injured"/"hurt"/"wounded" ->
     human_injured. Never combine a killed-count and an injured-count into
     the same field.
   - Extract numbers exactly as given; never round, estimate, or invent a
     count for a field that has no number in the headline (leave it 0).

AGGREGATE / AND-COUNTING / PERIOD-TOTAL DETECTION - report_type field

8. Every incident object MUST include a "report_type" field, set to either
   "single_incident" or "aggregate_period_total".

   Set report_type to "aggregate_period_total" if the headline reports a
   CUMULATIVE or RUNNING statistic spanning multiple separate attacks/events,
   rather than one specific dated attack. Strong signals of this (any ONE is
   enough):
   a. Two or more casualty/kill/injury numbers combined into one running
      total (e.g. "12 killed, 29 injured").
   b. A tally phrased as still accumulating: "and counting", "so far",
      "till date", "to date", or a total explicitly scoped to "this
      year"/"this season"/"this month" as the SUBJECT of the count (not
      just mentioned in passing).
   c. Explicit multi-event language: "attacks" (plural events), "series of
      attacks", "spate of attacks", "string of incidents", "repeated
      attacks", "in separate incidents", "across N villages/districts".
   d. A date range or comparison spanning more than one occasion (e.g.
      "over the past week", "in the last three months", "since January",
      "attacks up 40% from last year").

   When report_type is "aggregate_period_total": still extract and map the
   numbers given (per rules above) - do NOT discard the headline - but they
   represent a PERIOD TOTAL, not a single dated attack. Reflect this in the
   summary field (e.g. "...this year" / "...this season") so it's clear
   downstream that this row must not be summed together with individual
   single-incident rows covering the same period, or casualties will be
   double-counted.

   EXCEPTION - do not mark a headline as aggregate solely for mentioning a
   time period in passing, if it still centers on exactly ONE dated attack:
   a headline like "Leopard kills Uttarakhand boy, state's 9th animal
   conflict death this year" is report_type "single_incident" with
   human_dead = 1 (the "9th this year" is context, NEVER a count to extract).

   Example - mark aggregate_period_total (combined counts):
   Headline: "12 killed, 29 injured in leopard attacks in Uttarakhand this year"
   -> state: "Uttarakhand", species: "Leopard", conflict_type: "Human Death",
      human_dead: 12, human_injured: 29, livestock_killed: 0,
      report_type: "aggregate_period_total"

   Example - single_incident (yearly count is just context):
   Headline: "Leopard kills Uttarakhand boy, state's 9th animal conflict death this year"
   -> human_dead: 1, report_type: "single_incident"
"""
