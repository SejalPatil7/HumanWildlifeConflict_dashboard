"""
Builds targeted Google News RSS search queries from combinations of
(species x conflict-event phrase x region), instead of a small flat
list of hand-written strings.

Only combinations that make ecological sense are generated — e.g. Asian
Elephant is only queried against Uttarakhand, Snow Leopard is not queried
against Jammu (plains, not its range), Porcupine only gets crop-damage
phrasing rather than "attack" phrasing, etc. This keeps the query volume
high-precision instead of blowing up into a full cartesian product.
"""

# ---------------------------------------------------------------------
# Regions in scope
# ---------------------------------------------------------------------
REGIONS = [
    "Ladakh",
    "Kashmir",
    "Jammu",
    "Himachal Pradesh",
    "Uttarakhand",
]

# ---------------------------------------------------------------------
# Species known to be involved in human-wildlife conflict across
# Ladakh / Jammu & Kashmir / Himachal Pradesh / Uttarakhand, each mapped
# to the regions it's actually reported in and the event phrasing that
# actually shows up in regional news headlines for that species.
# ---------------------------------------------------------------------
SPECIES_CONFIG = {
    "Snow Leopard": {
        "regions": ["Ladakh", "Kashmir", "Himachal Pradesh", "Uttarakhand"],
        "events": ["attack", "livestock", "kills sheep", "kills goats"],
    },
    "Leopard": {
        "regions": ["Kashmir", "Jammu", "Himachal Pradesh", "Uttarakhand"],
        "events": ["attack", "mauls", "kills livestock", "human injured"],
    },
    "Himalayan Brown Bear": {
        "regions": ["Ladakh", "Himachal Pradesh", "Uttarakhand"],
        "events": ["attack", "mauls", "livestock"],
    },
    "Asiatic Black Bear": {
        "regions": ["Kashmir", "Jammu", "Himachal Pradesh", "Uttarakhand"],
        "events": ["attack", "mauls", "human injured"],
    },
    "Wolf": {
        "regions": ["Ladakh", "Himachal Pradesh", "Uttarakhand"],
        "events": ["attack", "livestock", "kills sheep"],
    },
    "Wild Boar": {
        "regions": ["Kashmir", "Jammu", "Himachal Pradesh", "Uttarakhand"],
        "events": ["crop raiding", "crop damage", "attack farmer"],
    },
    "Rhesus Macaque": {
        "regions": ["Jammu", "Himachal Pradesh", "Uttarakhand"],
        "events": ["crop raiding", "monkey menace", "attack villager"],
    },
    "Common Langur": {
        "regions": ["Himachal Pradesh", "Uttarakhand"],
        "events": ["crop raiding", "crop damage"],
    },
    "Asian Elephant": {
        "regions": ["Uttarakhand"],
        "events": ["attack", "tramples", "crop raiding", "human elephant conflict"],
    },
    "Nilgai": {
        "regions": ["Uttarakhand", "Himachal Pradesh"],
        "events": ["crop raiding", "crop damage"],
    },
    "Sambar Deer": {
        "regions": ["Uttarakhand", "Himachal Pradesh"],
        "events": ["crop raiding"],
    },
    "Porcupine": {
        "regions": ["Uttarakhand", "Himachal Pradesh"],
        "events": ["crop damage"],
    },
    "Golden Jackal": {
        "regions": ["Kashmir", "Jammu", "Himachal Pradesh", "Uttarakhand"],
        "events": ["attack", "livestock", "kills poultry"],
    },
}

# A handful of catch-all, non-species-specific queries per region, to
# still surface incidents that use generic phrasing.
GENERIC_EVENTS = ["human wildlife conflict", "wild animal attack"]


def build_queries():
    """Returns a deduplicated list of targeted query strings."""
    queries = []

    for species, cfg in SPECIES_CONFIG.items():
        for region in cfg["regions"]:
            for event in cfg["events"]:
                queries.append(f"{species} {event} {region}")

    for region in REGIONS:
        for event in GENERIC_EVENTS:
            queries.append(f"{event} {region}")

    # Preserve order, drop exact duplicates
    seen = set()
    deduped = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            deduped.append(q)

    return deduped


if __name__ == "__main__":
    qs = build_queries()
    print(f"Generated {len(qs)} targeted queries.")
    for q in qs[:15]:
        print(" -", q)
