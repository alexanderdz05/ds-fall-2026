import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="MovieLens Dashboard", layout="wide", page_icon="🎬")

# Shared Plotly layout applied to every figure
CHART_THEME = dict(
    template="plotly_white",
    font=dict(family="Inter, sans-serif"),
    title_font=dict(size=16),
    margin=dict(l=10, r=10, t=50, b=10),
)

GOLD   = "#e8a030"
BLUE   = "#4C72B0"
GREEN  = "#2e8b57"
RED    = "#c0392b"
PURPLE = "#7b4fa6"

@st.cache_data
def load_data():
    df = pd.read_csv("data/movie_ratings.csv")
    df["genres_list"] = df["genres"].str.split("|")
    exploded = df.explode("genres_list").copy()
    exploded = exploded[exploded["genres_list"].notna() & (exploded["genres_list"] != "")]
    return df, exploded

df, exploded = load_data()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🎬 MovieLens Dashboard")
st.caption("Exploring 100 K ratings across genres, years, and top films.")

# ── Metrics strip ─────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total ratings",     f"{len(df):,}")
m2.metric("Unique movies",     f"{df['movie_id'].nunique():,}")
m3.metric("Unique users",      f"{df['user_id'].nunique():,}")
m4.metric("Overall mean rating", f"{df['rating'].mean():.2f}")

st.divider()

# ── Sidebar controls ──────────────────────────────────────────────────────────
st.sidebar.markdown("## Controls")

all_genres = sorted(exploded["genres_list"].unique())
top5_genres = (
    exploded.drop_duplicates(subset=["movie_id", "genres_list"])
    ["genres_list"].value_counts().head(5).index.tolist()
)

selected_genres = st.sidebar.multiselect(
    "Filter by genre",
    options=all_genres,
    default=top5_genres,
    help="Applies to Charts 1 & 2",
)

year_min = int(df["year"].dropna().min())
year_max = int(df["year"].dropna().max())
year_range = st.sidebar.slider(
    "Release year range (Chart 3)",
    min_value=year_min, max_value=year_max,
    value=(year_min, year_max),
)

rating_floor = st.sidebar.slider(
    "Minimum ratings floor (Chart 4)",
    min_value=10, max_value=300, value=50, step=10,
    help="Raise or lower the floor to see how the Top 5 changes",
)

genre_df = exploded[exploded["genres_list"].isin(selected_genres)]

# ── Question 1: Genre Breakdown ───────────────────────────────────────────────
st.subheader("Question 1 — Genre Breakdown")
st.markdown("**What's the distribution of genres among the movies that were rated?**")

genre_counts = (
    genre_df.drop_duplicates(subset=["movie_id", "genres_list"])
    ["genres_list"].value_counts().sort_values(ascending=True).reset_index()
)
genre_counts.columns = ["genre", "count"]

fig1 = px.bar(
    genre_counts, x="count", y="genre", orientation="h",
    labels={"count": "Number of movies", "genre": "Genre"},
    title="Movies per genre",
    color="count",
    color_continuous_scale=[[0, "#3a4a7a"], [0.5, BLUE], [1, GOLD]],
)
fig1.update_coloraxes(showscale=False)
fig1.update_layout(**CHART_THEME, height=420,
                   yaxis={"categoryorder": "total ascending"})
fig1.update_traces(hovertemplate="<b>%{y}</b><br>Movies: %{x:,}<extra></extra>")
st.plotly_chart(fig1, use_container_width=True)

top_genre    = genre_counts.loc[genre_counts["count"].idxmax(), "genre"]
top_count    = genre_counts["count"].max()
bottom_genre = genre_counts.loc[genre_counts["count"].idxmin(), "genre"]
bottom_count = genre_counts["count"].min()

st.markdown(f"""
**What the data shows:** Among the selected genres, **{top_genre}** leads with **{top_count:,} movies**, while **{bottom_genre}** has the fewest at **{bottom_count:,}**. Add more genres from the sidebar to compare against the full distribution.
""")

st.divider()

# ── Question 2: Genre Satisfaction ────────────────────────────────────────────
st.subheader("Question 2 — Genre Satisfaction")
st.markdown("**Which genres have the highest average rating? Which have the lowest?**")

avg_rating = (
    genre_df.groupby("genres_list")["rating"].mean()
    .sort_values(ascending=True).reset_index()
)
avg_rating.columns = ["genre", "mean_rating"]
overall_mean = avg_rating["mean_rating"].mean()

bar_colors = [
    RED   if v == avg_rating["mean_rating"].min() else
    GREEN if v == avg_rating["mean_rating"].max() else
    BLUE
    for v in avg_rating["mean_rating"]
]

fig2 = go.Figure()
fig2.add_trace(go.Bar(
    x=avg_rating["mean_rating"], y=avg_rating["genre"],
    orientation="h", marker_color=bar_colors,
    marker_line_width=0,
    hovertemplate="<b>%{y}</b><br>Mean rating: %{x:.3f}<extra></extra>",
))
fig2.add_vline(
    x=overall_mean, line_dash="dot", line_color="#aaaaaa", line_width=1.5,
    annotation_text=f"mean {overall_mean:.2f}",
    annotation_position="top right",
    annotation_font=dict(color="#888888", size=11),
)
fig2.update_layout(
    **CHART_THEME, height=420,
    title="Average rating by genre",
    xaxis=dict(title="Mean rating", range=[0, 5]),
    yaxis=dict(title="", categoryorder="total ascending"),
)
st.plotly_chart(fig2, use_container_width=True)

best_genre  = avg_rating.loc[avg_rating["mean_rating"].idxmax(), "genre"]
worst_genre = avg_rating.loc[avg_rating["mean_rating"].idxmin(), "genre"]
spread = avg_rating["mean_rating"].max() - avg_rating["mean_rating"].min()

st.markdown(f"""
**Highest rated:** {best_genre} leads at **{avg_rating["mean_rating"].max():.2f}** (green). Niche/prestige genres attract fans who already love them, inflating averages.

**Lowest rated:** {worst_genre} sits at the bottom with **{avg_rating["mean_rating"].min():.2f}** (red).
""")

st.divider()

# ── Question 3: Ratings Over Time ─────────────────────────────────────────────
st.subheader("Question 3 — Ratings Over Time")
st.markdown("**How has the mean rating changed across movie release years?**")

time_df = df[df["year"].between(*year_range)].copy()
yearly = (
    time_df.groupby("year")["rating"]
    .agg(mean_rating="mean", count="count").reset_index()
)
yearly = yearly[yearly["count"] >= 5]
period_mean = yearly["mean_rating"].mean()

peak_year = int(yearly.loc[yearly["mean_rating"].idxmax(), "year"])
peak_val  = yearly["mean_rating"].max()
low_year  = int(yearly.loc[yearly["mean_rating"].idxmin(), "year"])
low_val   = yearly["mean_rating"].min()

fig3 = go.Figure()
fig3.add_trace(go.Scatter(
    x=yearly["year"], y=yearly["mean_rating"],
    mode="lines",
    line=dict(color=BLUE, width=2.5),
    fill="tozeroy",
    fillcolor="rgba(76,114,176,0.10)",
    hovertemplate="<b>%{x}</b><br>Mean rating: %{y:.3f}<br>Ratings: %{customdata:,}<extra></extra>",
    customdata=yearly["count"],
    name="Mean rating",
))
fig3.add_hline(
    y=period_mean, line_dash="dot", line_color="#aaaaaa", line_width=1.5,
    annotation_text=f"period mean {period_mean:.2f}",
    annotation_position="top right",
    annotation_font=dict(color="#888888", size=11),
)
fig3.update_layout(
    **CHART_THEME, height=420,
    title="Mean rating by movie release year",
    xaxis=dict(title="Release year"),
    yaxis=dict(title="Mean rating", range=[1, 5]),
    showlegend=False,
)
st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ── Question 4: Best Movies With a Floor ──────────────────────────────────────
st.subheader("Question 4 — Best Movies, With a Floor")
st.markdown(f"**Top 5 best-rated movies with at least {rating_floor} ratings** *(adjust the floor in the sidebar)*")

movie_stats = (
    df.groupby("title")["rating"]
    .agg(mean_rating="mean", count="count").reset_index()
)

top5 = (
    movie_stats[movie_stats["count"] >= rating_floor]
    .nlargest(5, "mean_rating")
    .sort_values("mean_rating", ascending=True)
)

# Color bars on a gold→green gradient by rank
n = len(top5)
bar_palette = px.colors.sample_colorscale(
    [[0, "#c87941"], [0.5, GOLD], [1, GREEN]],
    [i / max(n - 1, 1) for i in range(n)],
)

fig4 = go.Figure()
fig4.add_trace(go.Bar(
    x=top5["mean_rating"], y=top5["title"],
    orientation="h",
    marker_color=bar_palette,
    marker_line_width=0,
    customdata=top5["count"],
    hovertemplate="<b>%{y}</b><br>Mean rating: %{x:.3f}<br>Ratings: %{customdata:,}<extra></extra>",
))
fig4.update_layout(
    **CHART_THEME, height=350,
    title=f"Top 5 movies (floor = {rating_floor} ratings)",
    xaxis=dict(title="Mean rating", range=[0, 5.2]),
    yaxis=dict(title="", categoryorder="total ascending"),
)
st.plotly_chart(fig4, use_container_width=True)

floor_50_titles  = movie_stats[movie_stats["count"] >= 50].nlargest(5, "mean_rating")["title"].tolist()
floor_150_titles = movie_stats[movie_stats["count"] >= 150].nlargest(5, "mean_rating")["title"].tolist()
dropped = set(floor_50_titles) - set(floor_150_titles)
