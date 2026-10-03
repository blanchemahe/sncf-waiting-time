"""Model page: what a prediction model would change, and where."""

import altair as alt
import streamlit as st

from sncf_waiting_time.model import (
    PREDICTABLE,
    UNPREDICTABLE,
    classify_stations,
    errors_by_station,
    overall_errors,
)
from sncf_waiting_time.summaries import min_stops_for_period

TOP_STATIONS = 15
PROFILE_COLOURS = {PREDICTABLE: "#2a78d6", UNPREDICTABLE: "#eb6834"}
GROUP_READINGS = {
    "Which station it is": (
        "The gap is mostly a property of the place. Local causes, such as a "
        "timetable that no longer matches reality, matter more than what "
        "happened earlier on the journey."
    ),
    "Earlier stops of the same train": (
        "The gap travels with the train: what happened at its earlier stops "
        "carries on down the route."
    ),
    "Earlier trains at the same station": (
        "The gap builds up at the station: when the earlier trains were off "
        "there, the next ones tend to be off too."
    ),
    "Position in the day and on the route": (
        "The gap depends on when the train runs in the day and on how far "
        "along its route it is."
    ),
}

scored = st.session_state["scored"]
first_day, last_day = st.session_state["evaluation_days"]
importance = st.session_state["importance"]

st.title("What would a prediction model change?")
st.markdown(
    "**Use the filters on the left to explore the data yourself.** SNCF's "
    "data scientists built a model that corrects the announced wait in real "
    "time: for a train two stations away, it predicts the gap from what has "
    "just happened at the station and along the route of the train. It is a "
    "short-term tool: it does not forecast which stations will go wrong next "
    "month."
)
st.info(
    "**The model is judged on days it has never seen**: the "
    f"{first_day:%d/%m/%Y} to {last_day:%d/%m/%Y} period, set aside before "
    "training. The period filter on the left only has an effect within these "
    "days."
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
st.markdown(
    "The **fixed correction** needs no model: it shifts the wait announced at "
    "each station by the usual gap of that station. It is the cheapest "
    "improvement, and it already brings a large part of the gain. The "
    "**model** goes further by reacting to what is happening on the day."
)

# --- Where it helps -------------------------------------------------------
st.header("Where would it help, and where would it not?")
days = scored["date"].nunique()
min_stops = min_stops_for_period(days)
by_station = errors_by_station(scored)
by_station = by_station[by_station["stops"] >= min_stops]
classified = classify_stations(by_station, display_error)
flagged = classified[classified["profile"].isin(PROFILE_COLOURS)]

if flagged.empty:
    st.info(
        "With these filters, no station has both enough train stops and "
        "screens that are less accurate than average."
    )
else:
    predictable = flagged[flagged["profile"] == PREDICTABLE]
    unpredictable = flagged[flagged["profile"] == UNPREDICTABLE]

    column_1, column_2 = st.columns(2)
    column_1.metric("Stations with a predictable gap", len(predictable))
    column_2.metric("Stations with an unpredictable gap", len(unpredictable))
    st.markdown(
        "These are the stations whose screens are less accurate than average. "
        "They call for **two different actions**:\n\n"
        "- **Predictable gap**: the model removes a large part of the error. "
        "The gap follows a pattern, so the display can be corrected.\n"
        "- **Unpredictable gap**: even the model cannot anticipate it. "
        "Correcting the display will not help: the cause is in operations."
    )

    worst = flagged.sort_values("display_error", ascending=False).head(TOP_STATIONS)
    base = alt.Chart(worst).encode(y=alt.Y("gare:N", sort=None, title="Station"))
    bars = base.mark_bar().encode(
        x=alt.X("display_error:Q", title="Mean error (minutes)"),
        color=alt.Color(
            "profile:N",
            scale=alt.Scale(
                domain=list(PROFILE_COLOURS), range=list(PROFILE_COLOURS.values())
            ),
            legend=alt.Legend(title=None, orient="top"),
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
        f"model helps. Stations need at least {min_stops} train stops over the "
        "evaluation days to appear."
    )

    shorter = predictable[predictable["mean_gap"] > 0]["gare"].tolist()
    if shorter:
        st.markdown(
            "**Not every gap is a longer wait.** At "
            f"{', '.join(shorter)}, passengers usually wait *less* than "
            "announced. The previous page does not show these stations, as it "
            "counts waits that are too long, yet their screens are just as "
            "wrong."
        )

    with st.expander("See the figures for every station"):
        table = (
            classified.sort_values("display_error", ascending=False)
            .rename(
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
            .round(2)
        )
        st.dataframe(table, hide_index=True)

# --- What drives the gap --------------------------------------------------
st.header("What drives the gap: the station or the train?")
leading = importance.iloc[0]
st.markdown(
    f"The model relies most on this information: **{leading['group'].lower()}**, "
    f"which accounts for {leading['share']:.0f} % of what it learnt. "
    f"{GROUP_READINGS[leading['group']]}"
)
importance_chart = (
    alt.Chart(importance)
    .mark_bar()
    .encode(
        x=alt.X("share:Q", title="Share of what the model learnt (%)"),
        y=alt.Y("group:N", sort=None, title=None, axis=alt.Axis(labelLimit=320)),
        tooltip=[
            alt.Tooltip("group:N", title="Information"),
            alt.Tooltip("share:Q", title="Share (%)", format=".1f"),
        ],
    )
)
st.altair_chart(importance_chart)
st.caption(
    "This measures what the model uses, which is a strong hint but not a "
    "proof of what causes the gap. It is computed once on the whole model, so "
    "the filters do not change it."
)
