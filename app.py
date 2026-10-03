"""Streamlit app exploring platform waiting-time deviations."""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from sncf_waiting_time.data import load_data
from sncf_waiting_time.filters import (
    filter_by_date,
    filter_by_station,
    filter_by_stop_rank,
)
from sncf_waiting_time.summaries import (
    DEFAULT_THRESHOLD,
    daily_summary,
    key_figures,
    weekday_summary,
)

DATA_DIR = Path(__file__).parent / "data"
WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


@st.cache_data
def get_data() -> pd.DataFrame:
    """Load the train stops once and keep them in memory."""
    return load_data(DATA_DIR / "x_train.csv.gz", DATA_DIR / "y_train.csv.gz")


st.set_page_config(page_title="Platform waiting times", layout="wide")
data = get_data()

# --- Sidebar: the filters -------------------------------------------------
st.sidebar.header("Explore with your field knowledge")
st.sidebar.caption(
    "Narrow the analysis to the days, stations and stops you know best. "
    "Every figure and chart on the page follows your choices."
)

first_day = data["date"].min().date()
last_day = data["date"].max().date()
period = st.sidebar.date_input(
    "Which period do you want to look at?",
    value=(first_day, last_day),
    min_value=first_day,
    max_value=last_day,
    format="DD/MM/YYYY",
)

stations = st.sidebar.multiselect(
    "Which stations?",
    options=sorted(data["gare"].unique()),
    placeholder="All stations",
)
st.sidebar.caption(
    "Stations are anonymised: each three-letter code stands for a real "
    "station, but the list of names was not shared with us. Ask the "
    "Transilien data owners for the matching names."
)

lowest_rank = int(data["arret"].min())
highest_rank = int(data["arret"].max())
ranks = st.sidebar.slider(
    "Does the position of the stop on the route matter?",
    min_value=lowest_rank,
    max_value=highest_rank,
    value=(lowest_rank, highest_rank),
)
st.sidebar.caption(
    f"The position is the rank of the stop on the route of the train: "
    f"{lowest_rank} is its {lowest_rank}th stop. Keep the low ranks to look "
    "at the start of the routes, the high ranks to look at their end."
)

threshold = st.sidebar.slider(
    "From how many extra minutes is a wait too long?",
    min_value=1,
    max_value=5,
    value=DEFAULT_THRESHOLD,
)
st.sidebar.caption(
    f"We suggest {DEFAULT_THRESHOLD} minutes: a gap passengers notice on the "
    "platform, reached at about one stop in ten. Change it to match your own "
    "service standard."
)

# --- Apply the filters ----------------------------------------------------
if len(period) != 2:
    st.info("Pick a start date and an end date.")
    st.stop()

selection = filter_by_date(data, period[0], period[1])
selection = filter_by_stop_rank(selection, ranks[0], ranks[1])
if stations:
    selection = filter_by_station(selection, stations)

# --- Page: introduction ---------------------------------------------------
st.title("Platform waiting times: where and when the displays get it wrong")
st.markdown("**Use the filters on the left to explore the data yourself.**")
st.markdown(
    "This app supports the strategic programme launched by SNCF's leadership "
    "team to improve the experience of **passengers on their way to work**. "
    "Commuters travel every working day, and the wait on the platform is one "
    "of the moments they remember.\n\n"
    "On the platform, screens tell passengers how many minutes they will wait "
    "for their train. This app compares the **announced** wait with the "
    "**actual** wait on working days, Monday to Friday, to show where and when "
    "the gap is the widest.\n\n"
    "The objective is to provide your teams with a clear view of the data SNCF already holds, "
    "explore solutions to make the waiting times on the screens more "
    "reliable, and prioritise stations for the next works."
)

if selection.empty:
    st.warning("No train stop matches these filters.")
    st.stop()

# --- Page: headline figures -----------------------------------------------
st.header("How often is the announced wait wrong?")
figures = key_figures(selection, threshold)

column_1, column_2, column_3, column_4 = st.columns(4)
column_1.metric("Train stops analysed", f"{figures['stops']:,}")
column_2.metric(
    f"Waits at least {threshold} min longer than announced",
    f"{figures['long_wait_share']:.1f} %",
)
column_3.metric(
    "Stops where the announced wait was exact",
    f"{figures['exact_share']:.1f} %",
)
column_4.metric(
    "Average gap",
    f"{figures['mean_deviation']:.2f} min",
    help="Negative: on average, passengers wait longer than announced.",
)
st.caption(
    f"A wait is counted as too long when passengers wait at least {threshold} "
    "minute(s) more than the screen announced. You can change this threshold "
    "in the panel on the left."
)

# --- Page: differences between days ---------------------------------------
st.header("Are some days worse than others?")

st.subheader("Day by day")
st.bar_chart(
    daily_summary(selection, threshold),
    x="date",
    y="long_wait_share",
    x_label="Day",
    y_label="Share of waits that are too long (%)",
)
st.caption(
    "The data covers working days outside July and August: weekends and the "
    "summer show as empty periods."
)

st.subheader("By day of the week")
weekdays = weekday_summary(selection, threshold)
weekdays["day"] = weekdays["weekday"].map(lambda number: WEEKDAYS[number])
calmest = weekdays.loc[weekdays["long_wait_share"].idxmin()]
busiest = weekdays.loc[weekdays["long_wait_share"].idxmax()]
gap = busiest["long_wait_share"] - calmest["long_wait_share"]

if gap < 1:
    st.markdown(
        "**No day of the week stands out**: the share of waits that are too "
        f"long differs by only {gap:.1f} point between the best and the worst "
        "day."
    )
else:
    st.markdown(
        f"**{busiest['day']} is the worst day**: "
        f"{busiest['long_wait_share']:.1f} % of waits are too long, against "
        f"{calmest['long_wait_share']:.1f} % on {calmest['day']}."
    )

with st.expander("See the detail for each day of the week"):
    weekday_chart = (
        alt.Chart(weekdays)
        .mark_bar()
        .encode(
            x=alt.X("day:N", sort=None, title="Day of the week"),
            y=alt.Y("long_wait_share:Q", title="Share of waits that are too long (%)"),
            tooltip=[
                alt.Tooltip("day:N", title="Day"),
                alt.Tooltip(
                    "long_wait_share:Q", title="Waits too long (%)", format=".1f"
                ),
                alt.Tooltip("stops:Q", title="Train stops", format=","),
            ],
        )
    )
    st.altair_chart(weekday_chart)
