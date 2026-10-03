"""Tests for the model variables."""

import pandas as pd
import pytest

from sncf_waiting_time.features import (
    MODEL_FEATURES,
    add_history_spread,
    add_train_order,
    build_features,
    encode_station,
)


@pytest.fixture
def stops():
    """Build a small table of train stops over two days."""
    return pd.DataFrame(
        {
            "train": ["AAA", "AAA", "BBB", "CCC", "CCC"],
            "gare": ["KYF", "JLR", "KYF", "KYF", "EOH"],
            "date": pd.to_datetime(
                ["2023-04-03", "2023-04-03", "2023-04-03", "2023-04-04", "2023-04-04"]
            ),
            "arret": [8, 9, 8, 8, 10],
            "p2q0": [0.0, 1.0, -1.0, 0.0, 2.0],
            "p3q0": [0.0, 0.0, -2.0, 0.0, 0.0],
            "p4q0": [1.0, 0.0, 0.0, 0.0, -1.0],
            "p0q2": [-3.0, 1.0, 0.0, 0.0, 0.0],
            "p0q3": [-1.0, 0.0, 2.0, 0.0, 0.0],
            "p0q4": [-2.0, 1.0, 0.0, 0.0, 0.0],
        }
    )


def test_add_train_order_numbers_trains_within_each_day(stops):
    result = add_train_order(stops)
    assert result["train_order"].tolist() == [1, 1, 2, 1, 1]


def test_add_train_order_cycle_restarts(stops):
    six_trains = pd.DataFrame(
        {
            "train": ["A", "B", "C", "D", "E", "F"],
            "date": pd.to_datetime(["2023-04-03"] * 6),
        }
    )
    result = add_train_order(six_trains)
    assert result["train_cycle"].tolist() == [1, 2, 3, 4, 0, 1]


def test_add_history_spread_measures_station_history(stops):
    result = add_history_spread(stops)
    assert result["max_station"].tolist() == [1.0, 1.0, 0.0, 0.0, 2.0]
    assert result["min_station"].tolist() == [0.0, 0.0, -2.0, 0.0, -1.0]
    assert result["range_station"].tolist() == [1.0, 1.0, 2.0, 0.0, 3.0]


def test_add_history_spread_measures_train_history(stops):
    result = add_history_spread(stops)
    assert result["range_train"].tolist() == [2.0, 1.0, 2.0, 0.0, 0.0]


def test_encode_station_keeps_the_station_of_each_stop(stops):
    result = encode_station(stops, ["EOH", "JLR", "KYF"])
    assert result["station"].tolist() == ["KYF", "JLR", "KYF", "KYF", "EOH"]


def test_encode_station_uses_the_given_categories(stops):
    one_day = stops[stops["date"] == "2023-04-03"]
    result = encode_station(one_day, ["EOH", "JLR", "KYF"])
    assert list(result["station"].cat.categories) == ["EOH", "JLR", "KYF"]


def test_encode_station_unknown_station_is_left_empty(stops):
    result = encode_station(stops, ["KYF"])
    assert result["station"].isna().tolist() == [False, True, False, False, True]


def test_build_features_returns_model_columns(stops):
    features = build_features(stops, ["EOH", "JLR", "KYF"])
    assert list(features.columns) == MODEL_FEATURES
    assert len(features) == len(stops)


def test_build_features_leaves_input_unchanged(stops):
    columns_before = list(stops.columns)
    build_features(stops, ["EOH", "JLR", "KYF"])
    assert list(stops.columns) == columns_before
