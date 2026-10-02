"""Tests for the summary functions."""

import pandas as pd
import pytest

from sncf_waiting_time.summaries import (
    daily_summary,
    is_long_wait,
    key_figures,
    min_stops_for_period,
    station_ranking,
    weekday_summary,
)


@pytest.fixture
def stops():
    """Build a small table of six train stops over two days."""
    return pd.DataFrame(
        {
            "train": ["AAA", "AAA", "BBB", "BBB", "CCC", "CCC"],
            "gare": ["KYF", "JLR", "KYF", "JLR", "KYF", "EOH"],
            "date": pd.to_datetime(
                [
                    "2023-04-03",
                    "2023-04-03",
                    "2023-04-03",
                    "2023-04-03",
                    "2023-04-04",
                    "2023-04-04",
                ]
            ),
            "arret": [8, 9, 8, 9, 8, 10],
            "p0q0": [-2.0, 0.0, -4.0, 1.0, 0.0, -1.0],
        }
    )


def test_is_long_wait_flags_deviation_at_threshold(stops):
    assert is_long_wait(stops, 2).tolist() == [True, False, True, False, False, False]


def test_is_long_wait_higher_threshold_flags_fewer_stops(stops):
    assert is_long_wait(stops, 3).sum() == 1


def test_is_long_wait_rejects_non_positive_threshold(stops):
    with pytest.raises(ValueError):
        is_long_wait(stops, 0)


def test_key_figures_counts(stops):
    figures = key_figures(stops, 2)
    assert figures["stops"] == 6
    assert figures["stations"] == 3
    assert figures["days"] == 2


def test_key_figures_shares_and_mean(stops):
    figures = key_figures(stops, 2)
    assert figures["mean_deviation"] == pytest.approx(-1.0)
    assert figures["long_wait_share"] == pytest.approx(100 * 2 / 6)
    assert figures["exact_share"] == pytest.approx(100 * 2 / 6)


def test_key_figures_rejects_empty_table(stops):
    with pytest.raises(ValueError):
        key_figures(stops.iloc[0:0])


def test_daily_summary_has_one_row_per_day(stops):
    summary = daily_summary(stops, 2)
    assert summary["date"].tolist() == [
        pd.Timestamp(2023, 4, 3),
        pd.Timestamp(2023, 4, 4),
    ]
    assert summary["stops"].tolist() == [4, 2]


def test_daily_summary_measures_each_day(stops):
    summary = daily_summary(stops, 2)
    assert summary["mean_deviation"].tolist() == pytest.approx([-1.25, -0.5])
    assert summary["long_wait_share"].tolist() == pytest.approx([50.0, 0.0])


def test_weekday_summary_numbers_monday_as_zero(stops):
    summary = weekday_summary(stops, 2)
    assert summary["weekday"].tolist() == [0, 1]
    assert summary["stops"].tolist() == [4, 2]


def test_station_ranking_puts_most_affected_first(stops):
    ranking = station_ranking(stops, threshold=2, min_stops=1)
    assert ranking["gare"].tolist()[0] == "KYF"
    assert ranking["long_wait_share"].iloc[0] == pytest.approx(100 * 2 / 3)


def test_station_ranking_leaves_out_small_stations(stops):
    ranking = station_ranking(stops, threshold=2, min_stops=2)
    assert set(ranking["gare"]) == {"KYF", "JLR"}


def test_min_stops_for_period_grows_with_the_period():
    assert min_stops_for_period(91) == 455


def test_min_stops_for_period_never_goes_below_the_floor():
    assert min_stops_for_period(2) == 30


def test_min_stops_for_period_rejects_non_positive_days():
    with pytest.raises(ValueError):
        min_stops_for_period(0)
