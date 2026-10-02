"""Filter the table of train stops."""

from collections.abc import Iterable
from datetime import date

import pandas as pd


def filter_by_station(data: pd.DataFrame, stations: Iterable[str]) -> pd.DataFrame:
    """
    Keep the train stops made at the given stations.

    :param data: train stops, one row per stop
    :param stations: codes of the stations to keep
    :return: train stops made at these stations
    """
    return data[data["gare"].isin(list(stations))]


def filter_by_date(
    data: pd.DataFrame, start: str | date, end: str | date
) -> pd.DataFrame:
    """
    Keep the train stops made between two dates, both included.

    :param data: train stops, one row per stop
    :param start: first day to keep
    :param end: last day to keep
    :return: train stops made within the period
    """
    first_day = pd.Timestamp(start)
    last_day = pd.Timestamp(end)
    if first_day > last_day:
        raise ValueError(f"Start date {start} is after end date {end}")
    return data[data["date"].between(first_day, last_day)]


def filter_by_stop_rank(
    data: pd.DataFrame, min_rank: int, max_rank: int
) -> pd.DataFrame:
    """
    Keep the train stops whose rank along the route is within a range.

    The rank is the position of the stop on the route of the train:
    8 means the eighth stop. Both bounds are included.

    :param data: train stops, one row per stop
    :param min_rank: lowest rank to keep
    :param max_rank: highest rank to keep
    :return: train stops within the range of ranks
    """
    if min_rank > max_rank:
        raise ValueError(f"Lowest rank {min_rank} is above highest rank {max_rank}")
    return data[data["arret"].between(min_rank, max_rank)]
