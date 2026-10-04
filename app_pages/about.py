"""About page: where the data comes from and what limits the analysis."""

import streamlit as st

from sncf_waiting_time.model import TEST_DAYS

REPOSITORY = "https://github.com/blanchemahe/sncf-waiting-time"
CHALLENGE = "https://challengedata.ens.fr/challenges/166"

all_stops = st.session_state["all_stops"]
first_day = all_stops["date"].min()
last_day = all_stops["date"].max()
days = all_stops["date"].nunique()

st.title("Sources and limits: what to know before deciding")
st.markdown(
    "This page does not depend on the filters on the left. It describes the "
    "whole data set and what the analysis can and cannot tell you."
)

st.warning(
    "**This is a student project.** The business context, an SNCF strategic "
    "programme and its teams, is a fictional scenario written for a course. "
    "This app is not an SNCF product and does not speak for SNCF. The data "
    "and the results are real."
)

# --- Source ---------------------------------------------------------------
st.header("Where does the data come from?")
column_1, column_2, column_3 = st.columns(3)
column_1.metric("Train stops", f"{len(all_stops):,}")
column_2.metric("Stations", all_stops["gare"].nunique())
column_3.metric("Days", days)
st.markdown(
    "The data was published by **SNCF-Transilien** on the **Challenge Data** "
    f"platform run by ENS, for [challenge n°166]({CHALLENGE}), *Live "
    "prediction of platform waiting time*. It is reused here under the terms "
    "of that platform, which place the data under the Etalab Open Licence "
    "unless stated otherwise.\n\n"
    "Each row is one train stopping at one station on one day, between "
    f"{first_day:%d/%m/%Y} and {last_day:%d/%m/%Y}. The measure is the gap, "
    "in whole minutes, between the wait announced on the screens and the "
    "actual wait."
)

# --- Limits ---------------------------------------------------------------
st.header("What should you keep in mind?")
st.markdown(
    "1. **Stations and trains are anonymised.** Stations appear as "
    "three-letter codes and the list of names was not shared. With it, the "
    "analysis would be far more useful: real names, a map, and a link with "
    "what your teams know of each site.\n"
    "2. **There is no time of day.** The data gives the date of each stop, "
    "not its hour, so peak and off-peak hours cannot be told apart.\n"
    "3. **Only working days are covered**, Monday to Friday, outside July "
    f"and August: {days} days in all. Nothing here applies to weekends or "
    "to the summer.\n"
    f"4. **The model is judged on the {TEST_DAYS} most recent days**, set "
    "aside before training. Its accuracy on other periods is not known.\n"
    "5. **The model is a short-term tool.** It corrects the announced wait "
    "for a train two stations away. It does not forecast which stations "
    "will go wrong in the coming months.\n"
    "6. **The app shows where the screens are wrong, not why.** The causes "
    "suggested on the previous pages are leads to check in the field."
)

# --- Method and credits ---------------------------------------------------
st.header("How was this built?")
st.markdown(
    "The analysis and the model come from a group project in machine "
    "learning, on the same data challenge. That project blended four models "
    "to climb the leaderboard of the challenge. The model shown here is a "
    "single XGBoost model: it trains in seconds, is easier to explain, and has the best predictive power on its own ("
    "the blend marginal improvement on the leaderboard score was less than 1 %).\n\n"
    "This app, its tests and its packaging were built by Blanche Mahé for "
    "the course *Tooling for the Data Scientist*. The code, the tests and "
    f"the instructions to run the app are in the [GitHub repository]({REPOSITORY})."
)
