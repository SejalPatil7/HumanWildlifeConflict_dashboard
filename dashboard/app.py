import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Resolve paths relative to this file's location, not the working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "processed", "incidents.csv")

# ==========================================================
# PAGE CONFIG
# ==========================================================
st.set_page_config(
    page_title="Himalayan Conflict Ledger",
    page_icon="🏔️",
    layout="wide"
)

# ==========================================================
# DESIGN TOKENS
# ==========================================================
INK = "#20261F"
INK_SOFT = "#4B5449"
PAPER = "#EFEEE4"
CARD = "#FFFFFF"
LINE = "#DAD5C4"
RIDGE = "#33544A"
RIDGE_SOFT = "#7D9C8F"
RUST = "#A6472B"
OCHRE = "#B9862B"
MOSS = "#5C7A3F"
SLATE = "#47697E"
SAND = "#9C9782"

SPECIES_COLORS = {
    "Snow Leopard": SLATE,
    "Leopard": RUST,
    "Tiger": "#D08C2A",
    "Himalayan Brown Bear": "#7A4A28",
    "Asiatic Black Bear": RIDGE,
    "Wolf": "#5B4B6E",
    "Wild Boar": "#8A6A3D",
    "Rhesus Macaque": "#B3556B",
    "Common Langur": SAND,
    "Asian Elephant": "#3E6E6B",
    "Nilgai": MOSS,
    "Sambar Deer": "#C08A28",
    "Porcupine": "#6E655A",
    "Golden Jackal": "#C9A227",
    "Other": "#B9B4A4",
}

STATE_COLORS = {
    "Jammu & Kashmir": SLATE,
    "Ladakh": RIDGE,
    "Himachal Pradesh": RUST,
    "Uttarakhand": OCHRE,
    "Sikkim": MOSS,
    "Arunachal Pradesh": "#6E655A",
    "West Bengal": SAND,
}

CONFLICT_COLORS = {
    "Human Death": RUST,
    "Human Injury": OCHRE,
    "Livestock Attack": MOSS,
    "Retaliation Against Wildlife": SLATE,
    "Crop Raiding": "#6E655A",
    "Other": SAND,
}


def themed(fig, showlegend=True, legend_top=False):
    layout = dict(
        font=dict(family="IBM Plex Sans, Helvetica, sans-serif", color=INK, size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=28, b=30, l=10, r=10),
        showlegend=showlegend,
        hoverlabel=dict(bgcolor=CARD, bordercolor=LINE, font_color=INK),
    )
    if legend_top:
        layout["legend"] = dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            bgcolor="rgba(0,0,0,0)"
        )
    fig.update_layout(**layout)
    fig.update_xaxes(showgrid=False, linecolor=LINE, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=LINE, zeroline=False)
    return fig


# ==========================================================
# STYLE
# ==========================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'IBM Plex Sans', sans-serif;
}}
.main {{ background: {PAPER}; }}
.block-container {{ padding-top: 2rem; max-width: 1200px; }}
h1, h2, h3 {{ font-family: 'Fraunces', serif; color: {INK}; }}
hr {{ border-color: {LINE}; }}
section[data-testid="stSidebar"] {{
    background: {CARD};
    border-right: 1px solid {LINE};
}}
section[data-testid="stSidebar"] .stMarkdown p {{ color: {INK_SOFT}; }}

/* Hero */
.ledger-hero {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-bottom: 2px solid {INK};
    padding-bottom: 18px;
    margin-bottom: 6px;
}}
.ledger-title {{
    font-family: 'Fraunces', serif;
    font-size: 2.6rem;
    font-weight: 600;
    color: {INK};
    line-height: 1.1;
    margin: 0;
}}
.ledger-sub {{
    font-size: 0.98rem;
    color: {INK_SOFT};
    margin-top: 10px;
    max-width: 640px;
    line-height: 1.5;
}}
.ledger-tag {{
    text-align: right;
    font-size: 0.85rem;
    color: {INK_SOFT};
    line-height: 1.6;
}}
.ledger-tag b {{ color: {INK}; }}

/* Contour divider */
.contour {{ margin: 22px 0 30px 0; opacity: 0.9; }}

/* KPI cards */
.kpi-row {{ display: flex; gap: 16px; margin-bottom: 6px; }}
.kpi-card {{
    flex: 1;
    background: {CARD};
    border: 1px solid {LINE};
    border-left: 4px solid {RIDGE};
    border-radius: 4px;
    padding: 16px 18px;
}}
.kpi-value {{
    font-family: 'Fraunces', serif;
    font-size: 2.1rem;
    font-weight: 600;
    color: {INK};
    line-height: 1;
}}
.kpi-label {{
    font-size: 0.86rem;
    color: {INK_SOFT};
    margin-top: 6px;
}}
.kpi-sub {{
    font-size: 0.78rem;
    color: {SAND};
    margin-top: 8px;
    border-top: 1px solid {LINE};
    padding-top: 8px;
}}

/* Section headers */
.sec-head {{ display: flex; align-items: flex-start; gap: 12px; margin: 6px 0 18px 0; }}
.sec-tick {{ width: 4px; min-width: 4px; border-radius: 2px; margin-top: 6px; height: 26px; }}
.sec-title {{ font-family: 'Fraunces', serif; font-size: 1.4rem; font-weight: 600; color: {INK}; }}
.sec-desc {{ font-size: 0.88rem; color: {INK_SOFT}; margin-top: 2px; }}

/* Field note callout */
.field-note {{
    background: {CARD};
    border: 1px dashed {LINE};
    border-radius: 4px;
    padding: 16px 18px;
    font-size: 0.9rem;
    color: {INK_SOFT};
    line-height: 1.6;
}}
.field-note b {{ color: {INK}; }}

/* Pipeline steps */
.pipe-step {{ display: flex; gap: 14px; margin-bottom: 14px; align-items: flex-start; }}
.pipe-num {{
    width: 26px; height: 26px; min-width: 26px;
    border-radius: 50%;
    background: {RIDGE};
    color: {PAPER};
    font-size: 0.8rem;
    font-weight: 600;
    display: flex; align-items: center; justify-content: center;
}}
.pipe-text {{ font-size: 0.92rem; color: {INK_SOFT}; padding-top: 3px; line-height: 1.5; }}
.pipe-text b {{ color: {INK}; }}

/* Tabs */
button[data-baseweb="tab"] {{ font-family: 'Fraunces', serif; font-size: 1rem; }}

/* Footer */
.ledger-footer {{
    font-size: 0.82rem;
    color: {SAND};
    text-align: center;
    padding-top: 8px;
}}
</style>
""", unsafe_allow_html=True)

CONTOUR_SVG = f"""
<div class="contour">
<svg viewBox="0 0 1200 24" preserveAspectRatio="none" width="100%" height="24"
 xmlns="http://www.w3.org/2000/svg">
<path d="M0 12 Q 75 0 150 12 T 300 12 T 450 12 T 600 12 T 750 12 T 900 12 T 1050 12 T 1200 12"
 fill="none" stroke="{LINE}" stroke-width="1.5"/>
</svg>
</div>
"""


def section_head(title, desc="", color=RIDGE):
    st.markdown(f"""
    <div class="sec-head">
        <div class="sec-tick" style="background:{color}"></div>
        <div>
            <div class="sec-title">{title}</div>
            <div class="sec-desc">{desc}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def kpi_card(label, value, sub, color):
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color:{color}">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


# ==========================================================
# HERO
# ==========================================================
st.markdown(f"""
<div class="ledger-hero">
    <div>
        <p class="ledger-title">The Himalayan Conflict Ledger</p>
        <p class="ledger-sub">
            A running record of human-wildlife encounters across the Indian Himalayan
            Region, built from local news reporting and read into structured form.
            Built for the Nature Conservation Foundation's High Altitude Program.
        </p>
    </div>
    <div class="ledger-tag">
        <b>Indian Himalayan Region</b><br>
        Records from 2015 to 2026
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(CONTOUR_SVG, unsafe_allow_html=True)

# ==========================================================
# LOAD DATA
# ==========================================================
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)

    numeric_cols = ["human_dead", "human_injured", "livestock_killed", "confidence"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    text_cols = [
        "state", "district", "village", "species", "conflict_type",
        "summary", "source", "url", "headline", "report_type",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str).replace("", "Unknown")

    # needs_review is a QA flag column - leave genuinely blank when empty
    # rather than filling with "Unknown", so it stays usable for filtering.
    if "needs_review" in df.columns:
        df["needs_review"] = df["needs_review"].fillna("").astype(str)
    else:
        df["needs_review"] = ""

    if "report_type" not in df.columns:
        df["report_type"] = "single_incident"

    df["incident_date"] = pd.to_datetime(df["incident_date"], errors="coerce")
    return df


df_raw = load_data()
total_extracted = len(df_raw)

# ==========================================================
# CLEAN DATA
# ==========================================================
df = df_raw.copy()

# "Azad Kashmir" / "AJK" / "Pakistan" / "Khyber Pakhtunkhwa" are intentionally
# NOT mapped into "Jammu & Kashmir" - those are Pakistan-administered-Kashmir
# / Pakistan locations, not the Indian state.
STATE_MAP = {
    "Jammu Kashmir": "Jammu & Kashmir",
    "Jammu and Kashmir": "Jammu & Kashmir",
    "J&K": "Jammu & Kashmir",
    "Kashmir": "Jammu & Kashmir",
    "Himachal": "Himachal Pradesh",
}
df["state"] = df["state"].replace(STATE_MAP)

VALID_STATES = [
    "Jammu & Kashmir", "Ladakh", "Himachal Pradesh", "Uttarakhand",
    "Sikkim", "Arunachal Pradesh", "West Bengal",
]
in_scope_state = df["state"].isin(VALID_STATES)

SPECIES_MAP = {
    "Snow leopard": "Snow Leopard", "snow leopard": "Snow Leopard",
    "Black Bear": "Asiatic Black Bear", "Brown Bear": "Himalayan Brown Bear",
    "Bear": "Asiatic Black Bear", "Wild boar": "Wild Boar", "Boar": "Wild Boar",
    "Monkey": "Rhesus Macaque", "Macaque": "Rhesus Macaque",
    "Langur": "Common Langur", "Elephant": "Asian Elephant",
    "Blue Bull": "Nilgai", "Jackal": "Golden Jackal", "Sambar": "Sambar Deer",
    "tiger": "Tiger",
}
df["species"] = df["species"].replace(SPECIES_MAP)

VALID_SPECIES = list(SPECIES_COLORS.keys())[:-1]  # exclude "Other" itself
df["species_raw"] = df["species"]
df["species"] = df["species"].where(df["species"].isin(VALID_SPECIES), "Other")

CONFLICT_MAP = {
    "Attack": "Human Injury", "Attack on human": "Human Injury",
    "Attack on livestock": "Livestock Attack", "Livestock depredation": "Livestock Attack",
    "Crop damage": "Crop Raiding", "Crop raiding": "Crop Raiding",
    "Attack by locals": "Retaliation Against Wildlife",
}
df["conflict_type"] = df["conflict_type"].replace(CONFLICT_MAP)
VALID_CONFLICT_TYPES = list(CONFLICT_COLORS.keys())[:-1]
df["conflict_type"] = df["conflict_type"].where(
    df["conflict_type"].isin(VALID_CONFLICT_TYPES), "Other"
)

if "headline" not in df.columns:
    df["headline"] = df["summary"]

df = df.drop_duplicates(subset="headline")

# ==========================================================
# DISTRICT INFERENCE
# ==========================================================
DISTRICT_LOOKUP = {
    "kupwara": "Kupwara", "baramulla": "Baramulla", "bandipora": "Bandipora",
    "ganderbal": "Ganderbal", "srinagar": "Srinagar", "budgam": "Budgam",
    "pulwama": "Pulwama", "shopian": "Shopian", "anantnag": "Anantnag",
    "kulgam": "Kulgam", "poonch": "Poonch", "rajouri": "Rajouri",
    "doda": "Doda", "bhaderwah": "Bhaderwah", "leh": "Leh", "kargil": "Kargil",
    "nubra": "Nubra", "chamoli": "Chamoli", "uttarkashi": "Uttarkashi",
    "rudraprayag": "Rudraprayag", "pithoragarh": "Pithoragarh", "almora": "Almora",
    "bageshwar": "Bageshwar", "kinnaur": "Kinnaur", "kullu": "Kullu",
    "chamba": "Chamba", "spiti": "Spiti", "lahaul": "Lahaul and Spiti",
    "mandi": "Mandi", "bilaspur": "Bilaspur", "nainital": "Nainital",
    "pauri": "Pauri Garhwal", "tehri": "Tehri Garhwal", "bahraich": "Bahraich",
}


def infer_district(row):
    district = str(row["district"])
    if district not in ["", "Unknown", "nan"]:
        return district
    headline = row["headline"].lower()
    for key, value in DISTRICT_LOOKUP.items():
        if key in headline:
            return value
    return "Unknown"


df["district"] = df.apply(infer_district, axis=1)

# ==========================================================
# COORDINATES
# ==========================================================
DISTRICT_COORDS = {
    "Leh": (34.15, 77.58), "Kargil": (34.55, 76.13), "Nubra": (34.60, 77.55),
    "Kupwara": (34.53, 74.26), "Baramulla": (34.20, 74.36), "Bandipora": (34.42, 74.64),
    "Ganderbal": (34.23, 74.78), "Srinagar": (34.08, 74.79), "Budgam": (34.01, 74.73),
    "Pulwama": (33.87, 74.90), "Shopian": (33.72, 74.84), "Anantnag": (33.73, 75.15),
    "Kulgam": (33.64, 75.02), "Poonch": (33.77, 74.09), "Rajouri": (33.38, 74.31),
    "Doda": (33.15, 75.55), "Bhaderwah": (32.98, 75.72), "Kullu": (31.96, 77.11),
    "Chamba": (32.56, 76.13), "Kinnaur": (31.57, 78.22), "Lahaul and Spiti": (32.57, 77.04),
    "Spiti": (32.24, 78.03), "Chamoli": (30.40, 79.32), "Pithoragarh": (29.58, 80.22),
    "Uttarkashi": (30.73, 78.44), "Rudraprayag": (30.28, 78.98), "Almora": (29.60, 79.66),
    "Bageshwar": (29.84, 79.77), "Mandi": (31.71, 76.93), "Bilaspur": (31.34, 76.75),
    "Nainital": (29.38, 79.46), "Pauri Garhwal": (30.15, 78.78), "Tehri Garhwal": (30.38, 78.48),
    "Bahraich": (27.57, 81.60),
}
STATE_COORDS = {
    "Jammu & Kashmir": (33.8, 74.8), "Ladakh": (34.2, 77.6),
    "Himachal Pradesh": (31.8, 77.4), "Uttarakhand": (30.4, 79.2),
    "Sikkim": (27.6, 88.5), "Arunachal Pradesh": (28.2, 94.7),
    "West Bengal": (27.0, 88.3),
}


def get_coords(row):
    if row["district"] in DISTRICT_COORDS:
        return DISTRICT_COORDS[row["district"]]
    if row["state"] in STATE_COORDS:
        return STATE_COORDS[row["state"]]
    return (None, None)


coords = df.apply(get_coords, axis=1)
df["lat"] = coords.apply(lambda x: x[0])
df["lon"] = coords.apply(lambda x: x[1])

has_coords = df["lat"].notna() & df["lon"].notna()
in_scope = in_scope_state & has_coords
excluded_df = df[~in_scope].copy()
df = df[in_scope].copy()

df["severity"] = df["human_dead"] * 5 + df["human_injured"] * 2 + df["livestock_killed"]
df.loc[df["severity"] == 0, "severity"] = 1

# ==========================================================
# SIDEBAR FILTERS
# ==========================================================
st.sidebar.markdown("### Filter the record")

years = sorted(df["incident_date"].dt.year.dropna().unique())
selected_years = st.sidebar.multiselect("Year", years, default=years)

species_filter = st.sidebar.multiselect(
    "Species", sorted(df["species"].unique()), default=sorted(df["species"].unique())
)

conflict_filter = st.sidebar.multiselect(
    "Conflict type", sorted(df["conflict_type"].unique()),
    default=sorted(df["conflict_type"].unique())
)

state_filter = st.sidebar.multiselect(
    "State", sorted(df["state"].unique()), default=sorted(df["state"].unique())
)

st.sidebar.markdown("---")
include_aggregates = st.sidebar.toggle(
    "Include period-total headlines",
    value=False,
    help=(
        "Some headlines report a running total across many incidents "
        "(e.g. '12 killed, 29 injured in leopard attacks this year') "
        "rather than one dated attack. Leave this off for accurate totals - "
        "turning it on double-counts those casualties against attacks "
        "already recorded individually."
    ),
)

filtered = df[
    df["incident_date"].dt.year.isin(selected_years)
    & df["species"].isin(species_filter)
    & df["conflict_type"].isin(conflict_filter)
    & df["state"].isin(state_filter)
]

if not include_aggregates:
    n_aggregate_hidden = (filtered["report_type"] == "aggregate_period_total").sum()
    filtered = filtered[filtered["report_type"] != "aggregate_period_total"]
else:
    n_aggregate_hidden = 0

# ==========================================================
# KPI ROW
# ==========================================================
incidents_count = len(filtered)
injuries = int(filtered["human_injured"].sum())
fatalities = int(filtered["human_dead"].sum())
livestock = int(filtered["livestock_killed"].sum())


def top_contributor(frame, value_col, label_col):
    if frame.empty or frame[value_col].sum() == 0:
        return "No cases recorded in this view"
    top = frame.groupby(label_col)[value_col].sum().idxmax()
    return f"Most reported in {top}"


c1, c2, c3, c4 = st.columns(4)
with c1:
    casualty_share = 0
    if incidents_count:
        casualty_share = round(
            100 * len(filtered[filtered["conflict_type"].isin(["Human Death", "Human Injury"])])
            / incidents_count
        )
    kpi_card("Incidents on record", incidents_count,
             f"{casualty_share}% involve human injury or death", RIDGE)
with c2:
    kpi_card("Human injuries", injuries,
             top_contributor(filtered, "human_injured", "state"), OCHRE)
with c3:
    kpi_card("Human fatalities", fatalities,
             top_contributor(filtered, "human_dead", "state"), RUST)
with c4:
    kpi_card("Livestock lost", livestock,
             top_contributor(filtered, "livestock_killed", "species"), MOSS)

st.write("")

n_excluded_scope = len(excluded_df)
with st.expander(f"Data quality notes  ·  {total_extracted} extracted, {incidents_count} shown above"):
    st.markdown(f"""
<div class="field-note">
<b>{total_extracted}</b> incidents were extracted from headlines in total.<br><br>
<b>{n_excluded_scope}</b> were excluded because their state was outside the Indian
Himalayan Region, or missing - this includes any Azad Kashmir / Pakistan-side
stories, which are <b>not</b> merged into Jammu & Kashmir's totals.<br><br>
<b>{n_aggregate_hidden}</b> are period-total headlines currently excluded from the
totals above to avoid double-counting against individually reported attacks. Use
the sidebar toggle to include them as a rough upper bound instead.<br><br>
Species outside the standard list are bucketed as <b>Other</b> rather than dropped -
see the <code>species_raw</code> and <code>needs_review</code> columns in the
Ledger tab for detail.
</div>
""", unsafe_allow_html=True)

st.markdown(CONTOUR_SVG, unsafe_allow_html=True)

# ==========================================================
# TABS
# ==========================================================
tab_map, tab_trends, tab_species, tab_explorer = st.tabs(
    ["Geography", "Trends", "Species & conflict", "Ledger"]
)

# ---------------- GEOGRAPHY ----------------
with tab_map:
    section_head(
        "Where incidents are reported",
        "Marker size reflects severity - weighted by human deaths, injuries, and livestock lost.",
        RIDGE,
    )

    color_mode = st.segmented_control(
        "Color markers by", ["Species", "Conflict type", "Severity"],
        default="Species", label_visibility="collapsed"
    )

    if color_mode == "Conflict type":
        color_col, color_map, use_continuous = "conflict_type", CONFLICT_COLORS, False
    elif color_mode == "Severity":
        color_col, color_map, use_continuous = "severity", None, True
    else:
        color_col, color_map, use_continuous = "species", SPECIES_COLORS, False

    map_kwargs = dict(
        lat="lat", lon="lon", size="severity", hover_name="headline",
        hover_data={"district": True, "state": True, "conflict_type": True,
                    "severity": True, "lat": False, "lon": False},
        zoom=4, height=560,
    )
    if use_continuous:
        fig = px.scatter_map(filtered, color=color_col,
                              color_continuous_scale=[PAPER, OCHRE, RUST], **map_kwargs)
    else:
        fig = px.scatter_map(filtered, color=color_col,
                              color_discrete_map=color_map, **map_kwargs)

    fig.update_layout(map_style="carto-positron", margin=dict(l=0, r=0, t=0, b=0))
    fig = themed(fig, legend_top=True)
    st.plotly_chart(fig, width="stretch")

    st.write("")
    section_head("Top conflict hotspots", "Districts with the most reported incidents in this view.", OCHRE)
    hotspots = (
        filtered.groupby(["district", "state"]).size()
        .reset_index(name="Incidents").sort_values("Incidents", ascending=False).head(10)
    )
    fig = px.bar(hotspots, x="Incidents", y="district", orientation="h",
                 color="state", color_discrete_map=STATE_COLORS)
    fig.update_layout(yaxis_title="", yaxis=dict(categoryorder="total ascending"))
    fig = themed(fig, legend_top=True)
    st.plotly_chart(fig, width="stretch")

# ---------------- TRENDS ----------------
with tab_trends:
    section_head(
        "Reported incidents over time",
        "Monthly counts. Recent months should be read cautiously - reporting volume rises as news "
        "sources digitize archives, which can look like a spike in real conflict.",
        RIDGE,
    )

    timeline = (
        filtered.dropna(subset=["incident_date"])
        .groupby(filtered["incident_date"].dt.to_period("M")).size()
        .reset_index(name="Incidents")
    )
    timeline["Month"] = timeline["incident_date"].dt.to_timestamp()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timeline["Month"], y=timeline["Incidents"], mode="lines+markers",
        line=dict(color=RIDGE, width=2), marker=dict(size=5, color=RIDGE),
        fill="tozeroy", fillcolor="rgba(51,84,74,0.10)",
        hovertemplate="%{x|%b %Y}: %{y} incidents<extra></extra>",
    ))
    if not timeline.empty:
        peak = timeline.loc[timeline["Incidents"].idxmax()]
        fig.add_annotation(
            x=peak["Month"], y=peak["Incidents"], text=f"Peak: {int(peak['Incidents'])}",
            showarrow=True, arrowhead=0, arrowcolor=SAND, font=dict(color=INK_SOFT, size=11),
            ay=-28,
        )
    fig.update_xaxes(rangeslider_visible=True, title="")
    fig.update_yaxes(title="Reported incidents")
    fig = themed(fig, showlegend=False)
    st.plotly_chart(fig, width="stretch")

# ---------------- SPECIES & CONFLICT ----------------
with tab_species:
    left, right = st.columns(2)
    with left:
        section_head("Species involved", "Share of recorded incidents, by species.", SLATE)
        species_chart = filtered["species"].value_counts().reset_index()
        species_chart.columns = ["Species", "Incidents"]
        species_pct = species_chart["Incidents"] / max(species_chart["Incidents"].sum(), 1) * 100
        slice_text = [f"{p:.0f}%" if p >= 5 else "" for p in species_pct]
        fig = go.Figure(data=[go.Pie(
            labels=species_chart["Species"], values=species_chart["Incidents"],
            hole=0.5,
            marker=dict(colors=[SPECIES_COLORS.get(s, SAND) for s in species_chart["Species"]]),
            text=slice_text, textinfo="text", textposition="inside",
            insidetextorientation="radial", textfont=dict(size=12, color=CARD),
            hovertemplate="%{label}: %{percent} (%{value} incidents)<extra></extra>",
        )])
        fig = themed(fig)
        fig.update_layout(height=420, legend=dict(font=dict(size=11)))
        st.plotly_chart(fig, width="stretch")

    with right:
        section_head("Conflict type", "How each incident was classified.", OCHRE)
        conflict_chart = filtered["conflict_type"].value_counts().reset_index()
        conflict_chart.columns = ["Conflict Type", "Incidents"]
        fig = px.bar(conflict_chart.sort_values("Incidents"), x="Incidents", y="Conflict Type",
                     orientation="h")
        fig.update_traces(marker_color=RIDGE)
        fig.update_layout(yaxis_title="")
        fig = themed(fig, showlegend=False)
        fig.update_layout(height=420)
        st.plotly_chart(fig, width="stretch")

    st.write("")
    section_head("Incidents by state", "Where reports concentrate across the region.", RUST)
    state_chart = filtered["state"].value_counts().reset_index()
    state_chart.columns = ["State", "Incidents"]
    fig = px.bar(state_chart.sort_values("Incidents", ascending=False), x="State", y="Incidents",
                 color="State", color_discrete_map=STATE_COLORS)
    fig = themed(fig, showlegend=False)
    st.plotly_chart(fig, width="stretch")

    st.write("")
    section_head("State by species", "Where each species' conflict incidents concentrate.", MOSS)
    heat = filtered.groupby(["state", "species"]).size().reset_index(name="Count")
    fig = px.density_heatmap(
        heat, x="species", y="state", z="Count", text_auto=True,
        color_continuous_scale=[[0, PAPER], [0.5, RIDGE_SOFT], [1, RIDGE]],
    )
    fig.update_layout(xaxis_title="", yaxis_title="")
    fig = themed(fig, showlegend=False)
    st.plotly_chart(fig, width="stretch")

# ---------------- LEDGER ----------------
with tab_explorer:
    section_head("Incident ledger", "Search and export the underlying records.", RIDGE)

    search = st.text_input(
        "Search headlines", placeholder="e.g. Budgam, snow leopard, school...",
        label_visibility="collapsed"
    )
    table = filtered
    if search:
        table = table[table["headline"].str.contains(search, case=False, na=False)]

    show_cols = [
        "incident_date", "state", "district", "species", "conflict_type",
        "livestock_killed", "human_injured", "human_dead", "report_type",
        "headline", "source", "needs_review",
    ]
    show_cols = [c for c in show_cols if c in table.columns]

    st.dataframe(
        table[show_cols].sort_values("incident_date", ascending=False),
        width="stretch", hide_index=True, height=420,
    )

    st.caption(f"{len(table)} of {len(filtered)} filtered records shown.")

    download_df = filtered.drop(columns=["article_body"], errors="ignore")
    csv = download_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered dataset", csv,
                        file_name="filtered_hwc_incidents.csv", mime="text/csv")

st.markdown(CONTOUR_SVG, unsafe_allow_html=True)

# ==========================================================
# PIPELINE / ABOUT
# ==========================================================
section_head("How this ledger is built", "", SAND)

steps = [
    ("Collect", "News headlines gathered via targeted Google News RSS queries, "
                 "crossing species, conflict type, and region."),
    ("Classify", "Each headline is read by a language model, which discards "
                  "conservation, tourism, and survey stories that aren't conflict reports."),
    ("Extract", "Casualty counts, species, state, and conflict type are pulled "
                 "from the remaining headlines into structured fields."),
    ("Reconcile", "Running-total headlines (e.g. '12 killed this year') are tagged "
                   "separately so they don't inflate totals for single dated attacks."),
    ("Locate", "District and state are resolved to approximate coordinates for mapping."),
]
for i, (title, desc) in enumerate(steps, start=1):
    st.markdown(f"""
    <div class="pipe-step">
        <div class="pipe-num">{i}</div>
        <div class="pipe-text"><b>{title}.</b> {desc}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown(f"""
<p class="ledger-footer">
Research prototype for the Nature Conservation Foundation's High Altitude Program.
Showing {len(filtered)} verified single-incident conflict reports, of {total_extracted} extracted overall.
</p>
""", unsafe_allow_html=True)
