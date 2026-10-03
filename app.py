"""Entry point of the Streamlit app: data, filters and navigation."""

from pathlib import Path

import pandas as pd
import streamlit as st

from sncf_waiting_time.data import load_data
from sncf_waiting_time.filters import (
    filter_by_date,
    filter_by_station,
    filter_by_stop_rank,
)
from sncf_waiting_time.summaries import DEFAULT_THRESHOLD

DATA_DIR = Path(__file__).parent / "data"


@st.cache_data
def get_data() -> pd.DataFrame:
    """Load the train stops once and keep them in memory."""
    return load_data(DATA_DIR / "x_train.csv.gz", DATA_DIR / "y_train.csv.gz")


st.set_page_config(page_title="Platform waiting times", layout="wide")
data = get_data()

# --- Navigation: the pages of the app -------------------------------------
page = st.navigation(
    [
        st.Page("app_pages/overview.py", title="Overview", default=True),
        st.Page("app_pages/stations.py", title="Priority stations"),
    ]
)

# --- Sidebar: the filters, shared by every page ---------------------------
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

if selection.empty:
    st.warning("No train stop matches these filters.")
    st.stop()

# --- Hand the selection over to the page and display it -------------------
st.session_state["selection"] = selection
st.session_state["threshold"] = threshold
page.run()
