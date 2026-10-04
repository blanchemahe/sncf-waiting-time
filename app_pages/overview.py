"""Overview page: how often and when the announced wait is wrong."""

import altair as alt
import streamlit as st

from sncf_waiting_time.summaries import daily_summary, key_figures, weekday_summary

MAIN_COLOUR = st.get_option("theme.primaryColor")
WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

selection = st.session_state["selection"]
threshold = st.session_state["threshold"]
minutes = "minute" if threshold == 1 else "minutes"

# --- Introduction ---------------------------------------------------------
st.title("Platform waiting times: where and when the displays get it wrong")
st.markdown(
    "This app supports the strategic programme launched by SNCF's leadership "
    "team to improve the experience of **passengers on their way to work**. "
    "Commuters travel every working day, and the wait on the platform is one "
    "of the moments they remember.\n\n"
    "On the platform, screens tell passengers how many minutes they will wait "
    "for their train. This app compares the **announced** wait with the "
    "**actual** wait on working days, Monday to Friday, to show where and when "
    "the gap is the widest.\n\n"
    "The objective is to provide your teams with a clear view of the data "
    "SNCF already holds, and to explore solutions to make the waiting times on "
    "the screens more reliable and to prioritise stations for the next works.\n\n"
    ":green[**Use the filters on the left to explore the data yourself.**]"
)

# --- Headline figures -----------------------------------------------------
st.header("How often is the announced wait wrong?")
figures = key_figures(selection, threshold)

column_1, column_2, column_3, column_4 = st.columns(4)
column_1.metric("Train stops analysed", f"{figures['stops']:,}")
column_2.metric(
    "Waits too long\\*",
    f"{figures['long_wait_share']:.1f} %",
    help=f"Share of stops where passengers waited at least {threshold} "
    f"{minutes} more than announced.",
)
column_3.metric(
    "Announced wait exact",
    f"{figures['exact_share']:.1f} %",
    help="Share of stops where the actual wait matched the announced wait.",
)
column_4.metric(
    "Average gap",
    f"{figures['mean_deviation']:.2f} min",
    help="Negative: on average, passengers wait longer than announced.",
)
st.markdown(
    f"\\* A wait is too long when passengers wait at least "
    f":orange[**{threshold} {minutes}**] more than the screen announced. "
    f":orange[**You choose this threshold with the first filter on the left.**]"
)

# --- Differences between days ---------------------------------------------
st.header("Are some days worse than others?")

st.subheader("Day by day")
daily = daily_summary(selection, threshold)
best_day = daily.loc[daily["long_wait_share"].idxmin()]
worst_day = daily.loc[daily["long_wait_share"].idxmax()]

if len(daily) == 1:
    st.markdown(
        f"**Only one day is selected**: {worst_day['long_wait_share']:.1f} % "
        "of its waits are too long. Widen the period to compare days."
    )
else:
    st.markdown(
        "**Some days are far worse than others**: the share of waits that are "
        f"too long goes from {best_day['long_wait_share']:.1f} % on "
        f"{best_day['date']:%d/%m/%Y} to {worst_day['long_wait_share']:.1f} % "
        f"on {worst_day['date']:%d/%m/%Y}."
    )

st.bar_chart(
    daily,
    x="date",
    y="long_wait_share",
    x_label="Day",
    y_label="Share of waits that are too long (%)",
    color=MAIN_COLOUR,
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
    expander_label = (
        "We found no pattern, so this chart is folded away. Open it to check "
        "for yourself"
    )
else:
    st.markdown(
        f"**{busiest['day']} is the worst day**: "
        f"{busiest['long_wait_share']:.1f} % of waits are too long, against "
        f"{calmest['long_wait_share']:.1f} % on {calmest['day']}."
    )
    expander_label = "Open the chart to compare the days of the week"

with st.expander(expander_label):
    weekday_chart = (
        alt.Chart(weekdays)
        .mark_bar(color=MAIN_COLOUR)
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

# --- Link to the next page ------------------------------------------------
st.divider()
st.markdown(
    "**What comes next.** The calendar explains little: the bad days are not "
    "tied to a day of the week. The next page looks at **where** the gap "
    "occurs, station by station."
)
st.page_link("app_pages/stations.py", label="Go to Priority stations →")
