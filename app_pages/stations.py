"""Stations page: which stations are the most affected by long waits."""

import altair as alt
import pandas as pd
import streamlit as st

from sncf_waiting_time.filters import filter_by_station
from sncf_waiting_time.summaries import (
    MIN_STOPS_FLOOR,
    MIN_STOPS_PER_DAY,
    daily_summary,
    key_figures,
    min_stops_for_period,
    station_ranking,
)

MAIN_COLOUR = st.get_option("theme.primaryColor")
AVERAGE_COLOUR = "#3C3732"
TOP_STATIONS = 15

selection = st.session_state["selection"]
threshold = st.session_state["threshold"]

st.title("Priority stations: where do passengers wait longer than announced?")
st.markdown(
    "This page ranks the stations by how often passengers wait longer than "
    "the screen announced, to help you decide where to act first.\n\n"
    ":green[**Use the filters on the left to explore the data yourself.**]"
)

figures = key_figures(selection, threshold)
min_stops = min_stops_for_period(figures["days"])
ranking = station_ranking(selection, threshold, min_stops)

if ranking.empty:
    st.warning(
        f"No station has the {min_stops} train stops needed to be ranked over "
        "this selection. Widen the period or the range of stop positions."
    )
    st.stop()

# --- Ranking --------------------------------------------------------------
st.header("Which stations stand out?")
with st.container(border=True):
    st.markdown(
        f"**This ranking adapts to the period you selected.** Your selection "
        f"covers **{figures['days']} day(s)**, so a station needs at least "
        f"**{min_stops} train stops** to be ranked. **{len(ranking)} of "
        f"{figures['stations']} stations** qualify. Shorten the period and the "
        "minimum goes down with it."
    )
    st.caption(
        f"How the minimum is set: {MIN_STOPS_PER_DAY} train stops per day on "
        f"average over the period, and never fewer than {MIN_STOPS_FLOOR}. "
        "Below that, the share of a station rests on too few trains to be "
        "trusted: a station with 6 stops, 2 of them late, would top the "
        "ranking. This rule was set by the data team and cannot be changed "
        "here."
    )
worst = ranking.iloc[0]

column_1, column_2, column_3, column_4 = st.columns(4)
column_1.metric(
    "Stations ranked",
    f"{len(ranking)} of {figures['stations']}",
    help=f"A station needs at least {min_stops} train stops to be ranked.",
)
column_2.metric("Most affected station", worst["gare"])
column_3.metric(
    "Its waits too long",
    f"{worst['long_wait_share']:.1f} %",
    help="Share of its stops where passengers waited longer than announced, "
    "by at least the threshold set on the left.",
)
column_4.metric(
    "All selected stops",
    f"{figures['long_wait_share']:.1f} %",
    help="The same share, across all the train stops of the selection.",
)

top = ranking.head(TOP_STATIONS)
bars = (
    alt.Chart(top)
    .mark_bar(color=MAIN_COLOUR)
    .encode(
        x=alt.X("long_wait_share:Q", title="Share of waits that are too long (%)"),
        y=alt.Y("gare:N", sort=None, title="Station"),
        tooltip=[
            alt.Tooltip("gare:N", title="Station"),
            alt.Tooltip("long_wait_share:Q", title="Waits too long (%)", format=".1f"),
            alt.Tooltip("mean_deviation:Q", title="Average gap (min)", format=".2f"),
            alt.Tooltip("stops:Q", title="Train stops", format=","),
        ],
    )
)
average = pd.DataFrame({"average": [figures["long_wait_share"]]})
average_line = (
    alt.Chart(average)
    .mark_rule(color=AVERAGE_COLOUR, strokeDash=[4, 4])
    .encode(x="average:Q")
)
st.altair_chart(bars + average_line)
st.caption(
    f"The {len(top)} most affected stations. The dashed line is the share "
    "across all the selected stops."
)

with st.expander("See the full ranking"):
    table = ranking.rename(
        columns={
            "gare": "Station",
            "stops": "Train stops",
            "mean_deviation": "Average gap (min)",
            "long_wait_share": "Waits too long (%)",
        }
    ).round({"Average gap (min)": 2, "Waits too long (%)": 1})
    st.dataframe(table, hide_index=True)

# --- One station in detail ------------------------------------------------
st.header("How does one station behave over time?")
station = st.selectbox(
    "Choose a station (listed from the most to the least affected)",
    options=ranking["gare"].tolist(),
)
station_stops = filter_by_station(selection, [station])
station_figures = key_figures(station_stops, threshold)
difference = station_figures["long_wait_share"] - figures["long_wait_share"]

column_1, column_2, column_3 = st.columns(3)
column_1.metric("Train stops at this station", f"{station_figures['stops']:,}")
column_2.metric(
    "Waits that are too long",
    f"{station_figures['long_wait_share']:.1f} %",
    delta=f"{difference:+.1f} points vs all selected stops",
    delta_color="inverse",
)
column_3.metric(
    "Average gap",
    f"{station_figures['mean_deviation']:.2f} min",
    help="Negative: on average, passengers wait longer than announced.",
)

station_days = daily_summary(station_stops, threshold)
days_above = int((station_days["long_wait_share"] > figures["long_wait_share"]).sum())
days_observed = len(station_days)
share_above = days_above / days_observed

if share_above >= 0.8:
    reading = (
        f"**{station} is worse than the rest almost every day**: on "
        f"{days_above} of {days_observed} days. This points to a lasting "
        "cause, such as a timetable that no longer matches reality."
    )
elif share_above <= 0.2:
    reading = (
        f"**{station} is worse than the rest on a few days only**: "
        f"{days_above} of {days_observed}. This points to incidents rather "
        "than to a lasting cause."
    )
else:
    reading = (
        f"**{station} is worse than the rest on {days_above} of "
        f"{days_observed} days**: neither a constant gap nor a few isolated "
        "incidents. It deserves a closer look on the ground."
    )
st.success(reading)

st.bar_chart(
    station_days,
    x="date",
    y="long_wait_share",
    x_label="Day",
    y_label="Share of waits that are too long (%)",
    color=MAIN_COLOUR,
)
st.caption(
    "How to read this chart: a station above the rest every single day "
    "points to a lasting cause. A station with a few very bad days points to "
    "incidents."
)

# --- Link to the next page ------------------------------------------------
st.divider()
st.markdown(
    "**What comes next.** This ranking shows where passengers wait longer "
    "than announced. It does not say whether the gap could have been "
    "anticipated, and so corrected on the screens. The next page answers "
    "that with a prediction model."
)
st.page_link("app_pages/predictions.py", label="Go to What a model would change →")
