"""Summarise waiting-time deviations by day, weekday and station."""

import pandas as pd

from sncf_waiting_time.data import TARGET_COLUMN

DEFAULT_THRESHOLD = 2
DEFAULT_MIN_STOPS = 500
MIN_STOPS_PER_DAY = 5
MIN_STOPS_FLOOR = 30


def is_long_wait(data: pd.DataFrame, threshold: int = DEFAULT_THRESHOLD) -> pd.Series:
    """
    Flag the train stops where the wait was longer than announced.

    A stop is flagged when the real wait exceeded the announced wait by at
    least the threshold. In the data this is a deviation of minus the
    threshold or lower.

    :param data: train stops, one row per stop
    :param threshold: number of extra minutes from which a wait is long
    :return: True for each stop with a long wait
    """
    if threshold <= 0:
        raise ValueError(f"Threshold must be positive, got {threshold}")
    return data[TARGET_COLUMN] <= -threshold


def _summarise(data: pd.DataFrame, by: str, threshold: int) -> pd.DataFrame:
    """
    Count the stops and measure the deviations within each group.

    :param data: train stops, one row per stop
    :param by: column defining the groups
    :param threshold: number of extra minutes from which a wait is long
    :return: one row per group
    """
    flagged = data.assign(long_wait=is_long_wait(data, threshold))
    summary = flagged.groupby(by).agg(
        stops=(TARGET_COLUMN, "size"),
        mean_deviation=(TARGET_COLUMN, "mean"),
        long_wait_share=("long_wait", "mean"),
    )
    summary["long_wait_share"] = summary["long_wait_share"] * 100
    return summary.reset_index()


def key_figures(data: pd.DataFrame, threshold: int = DEFAULT_THRESHOLD) -> dict:
    """
    Compute the headline figures of a set of train stops.

    Shares are in percent.

    :param data: train stops, one row per stop
    :param threshold: number of extra minutes from which a wait is long
    :return: number of stops, stations and days, mean deviation, share of
        long waits and share of stops with no deviation
    """
    if data.empty:
        raise ValueError("No train stop to summarise")
    return {
        "stops": len(data),
        "stations": int(data["gare"].nunique()),
        "days": int(data["date"].nunique()),
        "mean_deviation": float(data[TARGET_COLUMN].mean()),
        "long_wait_share": float(is_long_wait(data, threshold).mean() * 100),
        "exact_share": float((data[TARGET_COLUMN] == 0).mean() * 100),
    }


def daily_summary(
    data: pd.DataFrame, threshold: int = DEFAULT_THRESHOLD
) -> pd.DataFrame:
    """
    Summarise the deviations for each day.

    :param data: train stops, one row per stop
    :param threshold: number of extra minutes from which a wait is long
    :return: one row per day, in chronological order
    """
    return _summarise(data, "date", threshold).sort_values("date", ignore_index=True)


def weekday_summary(
    data: pd.DataFrame, threshold: int = DEFAULT_THRESHOLD
) -> pd.DataFrame:
    """
    Summarise the deviations for each day of the week.

    The weekday is a number: 0 is Monday and 6 is Sunday.

    :param data: train stops, one row per stop
    :param threshold: number of extra minutes from which a wait is long
    :return: one row per day of the week, from Monday onwards
    """
    with_weekday = data.assign(weekday=data["date"].dt.dayofweek)
    summary = _summarise(with_weekday, "weekday", threshold)
    return summary.sort_values("weekday", ignore_index=True)


def station_ranking(
    data: pd.DataFrame,
    threshold: int = DEFAULT_THRESHOLD,
    min_stops: int = DEFAULT_MIN_STOPS,
) -> pd.DataFrame:
    """
    Rank the stations from the most to the least affected by long waits.

    Stations with too few stops are left out, as their share of long waits
    would rest on too little evidence.

    :param data: train stops, one row per stop
    :param threshold: number of extra minutes from which a wait is long
    :param min_stops: number of stops a station needs to be ranked
    :return: one row per station, the most affected first
    """
    summary = _summarise(data, "gare", threshold)
    ranked = summary[summary["stops"] >= min_stops]
    return ranked.sort_values("long_wait_share", ascending=False, ignore_index=True)


def min_stops_for_period(days: int) -> int:
    """
    Set how many stops a station needs to be ranked over a period.

    The minimum grows with the length of the period, so that a short
    period does not leave out most stations. It never goes below a floor,
    under which a share of long waits is not reliable.

    :param days: number of days in the period
    :return: number of stops a station needs to be ranked
    """
    if days <= 0:
        raise ValueError(f"Number of days must be positive, got {days}")
    return max(MIN_STOPS_FLOOR, MIN_STOPS_PER_DAY * days)
