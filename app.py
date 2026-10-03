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
from sncf_waiting_time.model import (
    group_importance,
    load_model,
    predict_gap,
    score_predictions,
    split_by_day,
    station_usual_gap,
)
from sncf_waiting_time.summaries import DEFAULT_THRESHOLD

DATA_DIR = Path(__file__).parent / "data"
MODEL_PATH = Path(__file__).parent / "models" / "waiting_time.json"


@st.cache_data
def get_data() -> pd.DataFrame:
    """Load the train stops once and keep them in memory."""
    return load_data(DATA_DIR / "x_train.csv.gz", DATA_DIR / "y_train.csv.gz")


@st.cache_data
def get_evaluation() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score the saved model once, on the days set aside from its training."""
    training, test = split_by_day(get_data())
    model = load_model(MODEL_PATH)
    scored = score_predictions(
        test, predict_gap(model, test), station_usual_gap(training)
    )
    return scored, group_importance(model)


st.set_page_config(page_title="Platform waiting times", layout="wide")
data = get_data()

# --- Navigation: the pages of the app -------------------------------------
page = st.navigation(
    [
        st.Page("app_pages/overview.py", title="Overview", default=True),
        st.Page("app_pages/stations.py", title="Priority stations"),
        st.Page("app_pages/predictions.py", title="What a model would change"),
        st.Page("app_pages/about.py", title="Sources and limits"),
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


def apply_filters(stops: pd.DataFrame) -> pd.DataFrame:
    """Keep the train stops matching the choices made in the sidebar."""
    kept = filter_by_date(stops, period[0], period[1])
    kept = filter_by_stop_rank(kept, ranks[0], ranks[1])
    if stations:
        kept = filter_by_station(kept, stations)
    return kept


selection = apply_filters(data)
if selection.empty:
    st.warning("No train stop matches these filters.")
    st.stop()

scored, importance = get_evaluation()

# --- Hand the selection over to the page and display it -------------------
st.session_state["all_stops"] = data
st.session_state["selection"] = selection
st.session_state["threshold"] = threshold
st.session_state["scored"] = apply_filters(scored)
st.session_state["evaluation_days"] = (scored["date"].min(), scored["date"].max())
st.session_state["importance"] = importance
page.run()
