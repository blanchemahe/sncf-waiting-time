"""Tests for the filtering functions."""

from datetime import date

import pandas as pd
import pytest

from sncf_waiting_time.filters import (
    filter_by_date,
    filter_by_station,
    filter_by_stop_rank,
)


@pytest.fixture
def stops():
    """Build a small table of five train stops."""
    return pd.DataFrame(
        {
            "train": ["AAA", "AAA", "BBB", "BBB", "CCC"],
            "gare": ["KYF", "JLR", "KYF", "EOH", "JLR"],
            "date": pd.to_datetime(
                ["2023-04-03", "2023-04-03", "2023-04-04", "2023-04-04", "2023-04-05"]
            ),
            "arret": [8, 9, 8, 10, 12],
            "p0q0": [-1.0, 0.0, 2.0, -3.0, 0.0],
        }
    )


def test_filter_by_station_keeps_one_station(stops):
    result = filter_by_station(stops, ["KYF"])
    assert len(result) == 2
    assert (result["gare"] == "KYF").all()


def test_filter_by_station_keeps_several_stations(stops):
    result = filter_by_station(stops, ["KYF", "EOH"])
    assert set(result["gare"]) == {"KYF", "EOH"}
    assert len(result) == 3


def test_filter_by_station_unknown_station_gives_empty_table(stops):
    result = filter_by_station(stops, ["ZZZ"])
    assert result.empty


def test_filter_by_station_leaves_input_unchanged(stops):
    filter_by_station(stops, ["KYF"])
    assert len(stops) == 5


def test_filter_by_date_includes_both_bounds(stops):
    result = filter_by_date(stops, "2023-04-03", "2023-04-04")
    assert len(result) == 4


def test_filter_by_date_accepts_date_objects(stops):
    result = filter_by_date(stops, date(2023, 4, 5), date(2023, 4, 5))
    assert result["train"].tolist() == ["CCC"]


def test_filter_by_date_start_after_end(stops):
    with pytest.raises(ValueError):
        filter_by_date(stops, "2023-04-05", "2023-04-03")


def test_filter_by_stop_rank_includes_both_bounds(stops):
    result = filter_by_stop_rank(stops, 9, 10)
    assert result["arret"].tolist() == [9, 10]


def test_filter_by_stop_rank_min_above_max(stops):
    with pytest.raises(ValueError):
        filter_by_stop_rank(stops, 12, 8)
