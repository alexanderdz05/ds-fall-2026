import calendar
from datetime import date, timedelta

import plotly.graph_objects as go
import requests
from dash import Dash, dcc, html


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


baseline_year, current_year, period_end, summary, source_note = load_data()
baseline_units = summary[baseline_year]["units"]
current_units = summary[current_year]["units"]
change_pct = (current_units / baseline_units - 1) * 100 if baseline_units else 0
change_label = f"{abs(change_pct):.1f}% {'lower' if change_pct < 0 else 'higher'}"

figure = go.Figure(
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
figure.update_layout(
	height=390,
	margin={"l": 24, "r": 24, "t": 36, "b": 50},
	paper_bgcolor="rgba(0,0,0,0)",
	plot_bgcolor="rgba(0,0,0,0)",
	font={"family": "Arial, sans-serif", "color": "#39433e", "size": 13},
	yaxis={"title": "Affordable units completed", "rangemode": "tozero", "showgrid": True, "gridcolor": "#e5e9e5", "zeroline": False},
	xaxis={"showgrid": False, "tickfont": {"size": 14}},
	showlegend=False,
	bargap=0.48,
)

app = Dash(__name__, title="Mamdani Housing Scorecard")
server = app.server

app.layout = html.Main(
	[
		html.Header(
			[
				html.Div("NEW YORK CITY  /  HOUSING", className="eyebrow"),
				html.H1("Is Mamdani moving the housing needle?"),
				html.P("An early read on completed affordable housing, using the city's own project records."),
			],
			className="masthead",
		),
		html.Section(
			[
				html.Div(
					[
						html.Div("THE SIGNAL", className="eyebrow"),
						html.Div(change_label, className="finding-number"),
						html.P(
							f"NYC recorded {current_units:,} affordable units completed from January through "
							f"{period_end:%B} {current_year}, compared with {baseline_units:,} in the same months of {baseline_year}.",
							className="finding-copy",
						),
					],
					className="finding",
				),
				html.Div(
					[
						html.H2("Affordable units completed"),
						html.P("Matched January-to-month-end periods", className="chart-subtitle"),
						dcc.Graph(figure=figure, config={"displayModeBar": False, "responsive": True}),
					],
					className="chart-section",
				),
			],
			className="content-grid",
		),
		html.Section(
			[
				html.H2("What this says, and what it doesn't"),
				html.P(
					f"The latest matched-period total is {change_label}. That is a negative early-term output signal, "
					"not a verdict on the mayor's full housing record. Affordable projects can take years to finance "
					"and build, so completions during 2026 often reflect decisions made before this administration. "
					"This measure counts affordable units HPD reports as completed; it does not measure market-rate "
					"construction, rent levels, housing quality, or total housing need."
				),
			],
			className="interpretation",
		),
		html.Footer(
			[
				html.Div([html.Span("SOURCE  ", className="source-label"), html.A("NYC HPD Affordable Housing Production by Project", href=DATASET_PAGE, target="_blank")]),
				html.Div(source_note, className="source-note"),
				html.Div(f"Completed units and projects; matched through {period_end:%b %d}. Counts are summed from HPD's all-counted-units field.", className="method-note"),
			],
			className="sources",
		),
	],
	className="page-shell",
)


if __name__ == "__main__":
	app.run(debug=False, host="0.0.0.0", port=8050)
