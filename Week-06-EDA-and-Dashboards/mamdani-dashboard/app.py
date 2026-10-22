import calendar
from datetime import date, timedelta

import plotly.graph_objects as go
import requests
import streamlit as st


DATASET_URL = "https://data.cityofnewyork.us/resource/hq68-rnsi.json"
DATASET_PAGE = "https://data.cityofnewyork.us/Housing-Development/Affordable-Housing-Production-by-Project/hq68-rnsi"
FALLBACK = {2025: {"units": 16468, "projects": 406}, 2026: {"units": 13078, "projects": 329}}


def get_period_end():
    first_of_this_month = date.today().replace(day=1)
    return first_of_this_month - timedelta(days=1)


def matched_period_end(period_end, year):
    last_day = calendar.monthrange(year, period_end.month)[1]
    return period_end.replace(year=year, day=min(period_end.day, last_day))


def fetch_summary(year, period_end):
    params = {
        "$select": "sum(all_counted_units) as units,count(project_id) as projects",
        "$where": (
            f"project_completion_date between '{year}-01-01T00:00:00' "
            f"and '{period_end:%Y-%m-%d}T23:59:59'"
        ),
    }
    response = requests.get(DATASET_URL, params=params, timeout=15)
    response.raise_for_status()
    row = response.json()[0]
    return {"units": int(row["units"] or 0), "projects": int(row["projects"] or 0)}


@st.cache_data(ttl=3600)
def load_data():
    period_end = get_period_end()
    current_year = period_end.year
    comparison_year = current_year - 1
    try:
        values = {
            comparison_year: fetch_summary(comparison_year, matched_period_end(period_end, comparison_year)),
            current_year: fetch_summary(current_year, period_end),
        }
        source_note = "Live values queried from NYC Open Data when this page loads."
    except (requests.RequestException, ValueError, KeyError, IndexError):
        values = FALLBACK
        current_year = 2026
        comparison_year = 2025
        period_end = date(2026, 9, 30)
        source_note = "Live data could not be reached; showing the verified Sep 30, 2026 snapshot."

    return comparison_year, current_year, period_end, values, source_note


st.set_page_config(page_title="Mamdani Housing Scorecard", layout="centered")

st.markdown("""
<style>
    .eyebrow { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.12em;
               text-transform: uppercase; color: #6b7a70; margin-bottom: 0.25rem; }
    .finding-number { font-size: 2.8rem; font-weight: 800; color: #d45432;
                      line-height: 1.1; margin: 0.25rem 0; }
    .source-label { font-weight: 700; font-size: 0.8rem; letter-spacing: 0.08em;
                    text-transform: uppercase; }
    .meta { font-size: 0.8rem; color: #6b7a70; }
    hr { border: none; border-top: 1px solid #e5e9e5; margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)

baseline_year, current_year, period_end, summary, source_note = load_data()
baseline_units = summary[baseline_year]["units"]
current_units = summary[current_year]["units"]
change_pct = (current_units / baseline_units - 1) * 100 if baseline_units else 0
change_label = f"{abs(change_pct):.1f}% {'lower' if change_pct < 0 else 'higher'}"

# Header
st.markdown('<div class="eyebrow">NEW YORK CITY &nbsp;/&nbsp; HOUSING</div>', unsafe_allow_html=True)
st.title("Is Mamdani moving the housing needle?")
st.write("An early read on completed affordable housing, using the city's own project records.")

st.markdown("<hr>", unsafe_allow_html=True)

# Signal metric + chart side by side
col_signal, col_chart = st.columns([1, 2], gap="large")

with col_signal:
    st.markdown('<div class="eyebrow">THE SIGNAL</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="finding-number">{change_label}</div>', unsafe_allow_html=True)
    st.write(
        f"NYC recorded {current_units:,} affordable units completed from January through "
        f"{period_end:%B} {current_year}, compared with {baseline_units:,} in the same months of {baseline_year}."
    )

with col_chart:
    st.subheader("Affordable units completed")
    st.caption("Matched January-to-month-end periods")

    fig = go.Figure(
        go.Bar(
            x=[f"Jan–{period_end:%b} {baseline_year}", f"Jan–{period_end:%b} {current_year}"],
            y=[baseline_units, current_units],
            marker_color=["#a7b5ad", "#d45432"],
            text=[f"{baseline_units:,}", f"{current_units:,}"],
            textposition="outside",
            textfont={"family": "Arial, sans-serif", "size": 16, "color": "#222a26"},
            hovertemplate="%{x}<br>%{y:,} affordable units<extra></extra>",
        )
    )
    fig.update_layout(
        height=340,
        margin={"l": 24, "r": 24, "t": 20, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Arial, sans-serif", "color": "#39433e", "size": 13},
        yaxis={
            "title": "Affordable units completed",
            "rangemode": "tozero",
            "showgrid": True,
            "gridcolor": "#e5e9e5",
            "zeroline": False,
        },
        xaxis={"showgrid": False, "tickfont": {"size": 14}},
        showlegend=False,
        bargap=0.48,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<hr>", unsafe_allow_html=True)

# Interpretation
st.subheader("What this says, and what it doesn't")
st.write(
    f"The latest matched-period total is {change_label}. That is a negative early-term output signal, "
    "not a verdict on the mayor's full housing record. Affordable projects can take years to finance "
    "and build, so completions during 2026 often reflect decisions made before this administration. "
    "This measure counts affordable units HPD reports as completed; it does not measure market-rate "
    "construction, rent levels, housing quality, or total housing need."
)

st.markdown("<hr>", unsafe_allow_html=True)

# Footer
st.markdown(
    f'<span class="source-label">SOURCE</span> &nbsp;<a href="{DATASET_PAGE}" target="_blank">'
    "NYC HPD Affordable Housing Production by Project</a>",
    unsafe_allow_html=True,
)
st.markdown(f'<div class="meta">{source_note}</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="meta">Completed units and projects; matched through {period_end:%b %d}. '
    "Counts are summed from HPD's all-counted-units field.</div>",
    unsafe_allow_html=True,
)
