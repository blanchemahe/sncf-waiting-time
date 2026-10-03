"""Build the variables the model uses to predict the waiting-time gap."""

from collections.abc import Iterable

import pandas as pd

STATION_HISTORY = ["p2q0", "p3q0", "p4q0"]
TRAIN_HISTORY = ["p0q2", "p0q3", "p0q4"]
CYCLE_LENGTH = 5

FEATURE_GROUPS = {
    "Earlier trains at the same station": [
        *STATION_HISTORY,
        "max_station",
        "min_station",
        "range_station",
    ],
    "Earlier stops of the same train": [
        *TRAIN_HISTORY,
        "max_train",
        "min_train",
        "range_train",
    ],
    "Which station it is": ["station"],
    "Position in the day and on the route": ["train_order", "train_cycle", "arret"],
}
MODEL_FEATURES = [name for group in FEATURE_GROUPS.values() for name in group]


def add_train_order(data: pd.DataFrame) -> pd.DataFrame:
    """
    Add the order of each train within its day and its place in a cycle.

    Trains are numbered from 1 in the order they first appear in the day.
    The cycle repeats every few trains, to capture recurring patterns.

    :param data: train stops, one row per stop
    :return: train stops with the columns train_order and train_cycle
    """
    order = data.groupby("date")["train"].transform(
        lambda trains: pd.factorize(trains)[0] + 1
    )
    return data.assign(train_order=order, train_cycle=order % CYCLE_LENGTH)


def add_history_spread(data: pd.DataFrame) -> pd.DataFrame:
    """
    Add the highest, lowest and range of the recent gaps.

    A wide range means the recent gaps were unstable, at the station or
    along the route of the train.

    :param data: train stops, one row per stop
    :return: train stops with six extra columns, three per history
    """
    spread = {}
    for name, columns in (("station", STATION_HISTORY), ("train", TRAIN_HISTORY)):
        highest = data[columns].max(axis=1)
        lowest = data[columns].min(axis=1)
        spread[f"max_{name}"] = highest
        spread[f"min_{name}"] = lowest
        spread[f"range_{name}"] = highest - lowest
    return data.assign(**spread)


def encode_station(data: pd.DataFrame, stations: Iterable[str]) -> pd.DataFrame:
    """
    Add the station as a category the model can read.

    The list of stations fixes the categories, so that the same station is
    always encoded the same way. A station missing from the list is left
    empty.

    :param data: train stops, one row per stop
    :param stations: every station code the model knows, in a fixed order
    :return: train stops with the column station
    """
    known_stations = list(stations)
    known = data["gare"].where(data["gare"].isin(known_stations))
    station = pd.Categorical(known, categories=known_stations)
    return data.assign(station=station)


def build_features(data: pd.DataFrame, stations: Iterable[str]) -> pd.DataFrame:
    """
    Build the table of variables given to the model.

    :param data: train stops, one row per stop
    :param stations: every station code the model knows, in a fixed order
    :return: one row per stop and one column per model variable
    """
    features = add_train_order(data)
    features = add_history_spread(features)
    features = encode_station(features, stations)
    return features[MODEL_FEATURES]
