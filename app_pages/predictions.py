"""Model page: what a prediction model would change, and where."""

import altair as alt
import streamlit as st

from sncf_waiting_time.model import (
    ACCURATE,
    MIN_ERROR_REDUCTION,
    PREDICTABLE,
    UNPREDICTABLE,
    classify_stations,
    errors_by_station,
    overall_errors,
)
from sncf_waiting_time.summaries import MIN_STOPS_PER_DAY, min_stops_for_period

MAIN_COLOUR = st.get_option("theme.primaryColor")
TOP_STATIONS = 15
PROFILE_LABELS = {PREDICTABLE: "Predictable gap", UNPREDICTABLE: "Unpredictable gap"}
PROFILE_COLOURS = {"Predictable gap": "#82BE00", "Unpredictable gap": "#E05206"}
HIGHLIGHT_COLOUR = "#D9EDB0"
GROUP_READINGS = {
    "Which station it is": (
        "In plain terms, the gap is mostly a property of the place: once you "
        "know the station, you already know most of what there is to know. "
        "Local causes, such as a timetable that no longer matches reality, "
        "weigh more than what happened earlier on the journey of the train."
    ),
    "Earlier stops of the same train": (
        "In plain terms, the gap travels with the train: what happened at its "
        "earlier stops carries on down the route."
    ),
    "Earlier trains at the same station": (
        "In plain terms, the gap builds up at the station: when the earlier "
        "trains were off there, the next ones tend to be off too."
    ),
    "Position in the day and on the route": (
        "In plain terms, the gap depends on when the train runs in the day "
        "and on how far along its route it is."
    ),
}

scored = st.session_state["scored"]
first_day, last_day = st.session_state["evaluation_days"]
importance = st.session_state["importance"]

st.title("What would a prediction model change?")
st.markdown(
    "SNCF's data scientists built a model that corrects the announced wait in "
    "real time: for a train two stations away, it predicts the gap from what "
    "has just happened at the station and along the route of the train. It is "
    "a short-term tool: it does not forecast which stations will go wrong "
    "next month.\n\n"
    ":green[**Use the filters on the left to explore the data yourself.**]"
)
with st.container(border=True):
    st.markdown(
        "**The model is judged on days it has never seen**: the "
        f"{first_day:%d/%m/%Y} to {last_day:%d/%m/%Y} period, set aside before "
        "training. The period filter on the left only has an effect within "
        "these days."
    )

if scored.empty:
    st.warning(
        "No train stop of the evaluation period matches these filters. Widen "
        "the period so that it includes days from "
        f"{first_day:%d/%m/%Y} onwards."
    )
    st.stop()

# --- How much more accurate -----------------------------------------------
st.header("How much more accurate could the screens be?")
errors = overall_errors(scored)
display_error = errors["display_error"]


def change(error: float) -> str:
    """Write an error as a change in percent against the screens today."""
    return f"{100 * (error / display_error - 1):+.0f} % vs today"


column_1, column_2, column_3 = st.columns(3)
column_1.metric("Mean error of the screens today", f"{display_error:.2f} min")
column_2.metric(
    "With a fixed correction per station",
    f"{errors['correction_error']:.2f} min",
    delta=change(errors["correction_error"]),
    delta_color="inverse",
)
column_3.metric(
    "With the prediction model",
    f"{errors['model_error']:.2f} min",
    delta=change(errors["model_error"]),
    delta_color="inverse",
)

model_gain = display_error - errors["model_error"]
correction_gain = display_error - errors["correction_error"]
if model_gain > 0 and correction_gain > 0:
    st.success(
        f"**{100 * correction_gain / model_gain:.0f} % of the gain needs no "
        "model.** A fixed correction shifts the wait announced at each station "
        "by the usual gap of that station. It is the cheapest improvement. "
        "The model goes further by reacting to what is happening on the day."
    )
else:
    st.markdown(
        "The **fixed correction** shifts the wait announced at each station by "
        "the usual gap of that station, without any model. The **model** "
        "reacts to what is happening on the day."
    )

# --- Where it helps -------------------------------------------------------
st.header("Where would it help, and where would it not?")
days = scored["date"].nunique()
min_stops = min_stops_for_period(days)
by_station = errors_by_station(scored)
enough_stops = by_station[by_station["stops"] >= min_stops]
classified = classify_stations(enough_stops, display_error)
flagged = classified[classified["profile"] != ACCURATE]
assessed = len(classified)

with st.container(border=True):
    st.markdown(
        f"**{assessed} of {len(by_station)} stations are assessed.** As on the "
        f"previous page, a station needs {MIN_STOPS_PER_DAY} train stops per "
        f"day on average to be assessed: {min_stops} stops over the {days} "
        "evaluation day(s) of your selection."
    )

if flagged.empty:
    st.info(
        "With these filters, no assessed station has screens that are less "
        "accurate than average."
    )
else:
    predictable = flagged[flagged["profile"] == PREDICTABLE]
    unpredictable = flagged[flagged["profile"] == UNPREDICTABLE]

    column_1, column_2, column_3 = st.columns(3)
    column_1.metric("Predictable gap", f"{len(predictable)} of {assessed}")
    column_2.metric("Unpredictable gap", f"{len(unpredictable)} of {assessed}")
    column_3.metric(
        "No action needed",
        f"{assessed - len(flagged)} of {assessed}",
        help="Stations whose screens are at least as accurate as the "
        "average of the selection.",
    )
    st.markdown(
        "The third group needs no action: its screens are at least as "
        "accurate as the average of the selection. The first two groups are "
        "the stations whose screens are less accurate than average. They call "
        "for **two different actions**:\n\n"
        f"- **Predictable gap**: the model removes at least "
        f"{MIN_ERROR_REDUCTION:.0f} % of the error. The gap follows a pattern, "
        "so the display can be corrected.\n"
        f"- **Unpredictable gap**: the model removes less than "
        f"{MIN_ERROR_REDUCTION:.0f} % of the error. Correcting the display "
        "will not help: the cause is in operations."
    )

    worst = flagged.sort_values("display_error", ascending=False).head(TOP_STATIONS)
    worst = worst.assign(group=worst["profile"].map(PROFILE_LABELS))
    base = alt.Chart(worst).encode(y=alt.Y("gare:N", sort=None, title="Station"))
    bars = base.mark_bar().encode(
        x=alt.X("display_error:Q", title="Mean error (minutes)"),
        color=alt.Color(
            "group:N",
            scale=alt.Scale(
                domain=list(PROFILE_COLOURS), range=list(PROFILE_COLOURS.values())
            ),
            legend=alt.Legend(title=None, orient="top", labelLimit=0),
        ),
        tooltip=[
            alt.Tooltip("gare:N", title="Station"),
            alt.Tooltip("display_error:Q", title="Error today (min)", format=".2f"),
            alt.Tooltip("model_error:Q", title="Error with model (min)", format=".2f"),
            alt.Tooltip("error_reduction:Q", title="Error removed (%)", format=".0f"),
            alt.Tooltip("mean_gap:Q", title="Usual gap (min)", format=".2f"),
            alt.Tooltip("stops:Q", title="Train stops", format=","),
        ],
    )
    points = base.mark_point(
        filled=True, color="white", stroke="black", size=70, opacity=1
    ).encode(x="model_error:Q")
    st.altair_chart(bars + points)
    st.caption(
        f"The {len(worst)} stations where the screens are the least accurate. "
        "The bar is the error today, the white dot is the error with the "
        "model: the further the dot from the end of the bar, the more the "
        "model helps."
    )

    shorter = predictable[predictable["mean_gap"] > 0]["gare"].tolist()
    if shorter:
        st.success(
            "**Not every gap is a longer wait.** At "
            f"{', '.join(shorter)}, passengers usually wait *less* than "
            "announced. The previous page does not show these stations, as it "
            "counts waits that are too long, yet their screens are just as "
            "wrong. They are highlighted in the table below."
        )
        expander_label = (
            "See the figures for every station (highlighted: passengers wait "
            "less than announced)"
        )
    else:
        expander_label = "See the figures for every station"

    with st.expander(expander_label):
        table = classified.sort_values("display_error", ascending=False).rename(
            columns={
                "gare": "Station",
                "stops": "Train stops",
                "mean_gap": "Usual gap (min)",
                "display_error": "Error today (min)",
                "correction_error": "Error with fixed correction (min)",
                "model_error": "Error with model (min)",
                "error_reduction": "Error removed by model (%)",
                "profile": "Profile",
            }
        )

        def highlight(row):
            """Colour the stations where passengers wait less than announced."""
            colour = HIGHLIGHT_COLOUR if row["Station"] in shorter else ""
            return [f"background-color: {colour}" if colour else ""] * len(row)

        styled = table.style.apply(highlight, axis=1).format(precision=2)
        st.dataframe(styled, hide_index=True)

# --- What drives the gap --------------------------------------------------
st.header("What drives the gap: the station or the train?")
leading = importance.iloc[0]
st.markdown(
    "To predict the gap, the model combines four kinds of information. The "
    "chart shows how much each one weighs in its predictions."
)
importance_chart = (
    alt.Chart(importance)
    .mark_bar(color=MAIN_COLOUR)
    .encode(
        x=alt.X("share:Q", title="Weight in the predictions of the model (%)"),
        y=alt.Y("group:N", sort=None, title=None, axis=alt.Axis(labelLimit=320)),
        tooltip=[
            alt.Tooltip("group:N", title="Information"),
            alt.Tooltip("share:Q", title="Weight (%)", format=".1f"),
        ],
    )
)
st.altair_chart(importance_chart)
st.success(
    f"**The information that counts most is: {leading['group'].lower()}.** It "
    f"carries {leading['share']:.0f} % of the weight in the predictions. "
    f"{GROUP_READINGS[leading['group']]}"
)
st.caption(
    "This shows what the model relies on, which is a strong hint but not a "
    "proof of what causes the gap. It is computed once on the whole model, so "
    "the filters do not change it."
)

# --- Link to the next page ------------------------------------------------
st.divider()
st.markdown(
    "**What comes next.** Two actions come out of this page: correct the "
    "display where the gap is predictable, and look at operations where it is "
    "not. Before acting on them, the last page states where the data comes "
    "from and what this analysis cannot tell."
)
st.page_link("app_pages/about.py", label="Go to Sources and limits →")
