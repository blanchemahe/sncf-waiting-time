"""Tests for the model training and evaluation."""

import random

import pandas as pd
import pytest

from sncf_waiting_time.features import FEATURE_GROUPS
from sncf_waiting_time.model import (
    ACCURATE,
    PREDICTABLE,
    UNPREDICTABLE,
    classify_stations,
    errors_by_station,
    group_importance,
    load_model,
    overall_errors,
    predict_gap,
    save_model,
    score_predictions,
    split_by_day,
    station_usual_gap,
    train_model,
)

STATIONS = ["AAA", "BBB", "CCC"]
HISTORY = ["p2q0", "p3q0", "p4q0", "p0q2", "p0q3", "p0q4"]


@pytest.fixture
def stops():
    """Generate 600 train stops over six days, with a gap that can be learnt."""
    generator = random.Random(0)
    rows = []
    for number in range(600):
        row = {
            "train": f"T{number % 40}",
            "gare": generator.choice(STATIONS),
            "date": pd.Timestamp(2023, 4, 3) + pd.Timedelta(days=number % 6),
            "arret": generator.randint(8, 20),
        }
        for column in HISTORY:
            row[column] = float(generator.randint(-3, 3))
        row["p0q0"] = row["p0q2"] - 2.0 * (row["gare"] == "AAA")
        rows.append(row)
    return pd.DataFrame(rows)


@pytest.fixture
def model(stops):
    """Train a small model on the generated stops."""
    return train_model(stops, STATIONS, rounds=20)


@pytest.fixture
def scored():
    """Build four scored stops whose errors are known."""
    data = pd.DataFrame(
        {
            "gare": ["AAA", "AAA", "BBB", "BBB"],
            "p0q0": [-2.0, -4.0, 0.0, 1.0],
        }
    )
    predictions = pd.Series([-2.4, -2.6, 0.2, 0.0])
    usual_gap = pd.Series({"AAA": -3.0, "BBB": 0.0})
    return score_predictions(data, predictions, usual_gap)


def test_split_by_day_sets_the_latest_days_aside(stops):
    training, test = split_by_day(stops, test_days=2)
    assert training["date"].nunique() == 4
    assert test["date"].nunique() == 2
    assert training["date"].max() < test["date"].min()


def test_split_by_day_keeps_every_stop(stops):
    training, test = split_by_day(stops, test_days=2)
    assert len(training) + len(test) == len(stops)


def test_split_by_day_rejects_too_many_days(stops):
    with pytest.raises(ValueError):
        split_by_day(stops, test_days=6)


def test_predict_gap_returns_one_value_per_stop(stops, model):
    predictions = predict_gap(model, stops)
    assert len(predictions) == len(stops)
    assert predictions.index.equals(stops.index)


def test_model_learns_the_gap(stops, model):
    predictions = predict_gap(model, stops)
    model_error = (stops["p0q0"] - predictions).abs().mean()
    display_error = stops["p0q0"].abs().mean()
    assert model_error < display_error


def test_saved_model_gives_the_same_predictions(stops, model, tmp_path):
    path = tmp_path / "models" / "model.json"
    save_model(model, path)
    reloaded = load_model(path)
    assert predict_gap(reloaded, stops).tolist() == predict_gap(model, stops).tolist()


def test_station_usual_gap_is_the_median_of_each_station():
    data = pd.DataFrame(
        {"gare": ["AAA", "AAA", "AAA", "BBB"], "p0q0": [-1.0, -2.0, -9.0, 1.0]}
    )
    usual_gap = station_usual_gap(data)
    assert usual_gap["AAA"] == -2.0
    assert usual_gap["BBB"] == 1.0


def test_score_predictions_measures_each_method(scored):
    assert scored["display_error"].tolist() == [2.0, 4.0, 0.0, 1.0]
    assert scored["correction_error"].tolist() == [1.0, 1.0, 0.0, 1.0]
    assert scored["model_error"].tolist() == [0.0, 1.0, 0.0, 1.0]


def test_errors_by_station_averages_each_station(scored):
    summary = errors_by_station(scored).set_index("gare")
    assert summary.loc["AAA", "stops"] == 2
    assert summary.loc["AAA", "mean_gap"] == pytest.approx(-3.0)
    assert summary.loc["AAA", "display_error"] == pytest.approx(3.0)
    assert summary.loc["AAA", "model_error"] == pytest.approx(0.5)
    assert summary.loc["BBB", "display_error"] == pytest.approx(0.5)


def test_overall_errors_averages_all_stops(scored):
    errors = overall_errors(scored)
    assert errors["display_error"] == pytest.approx(1.75)
    assert errors["correction_error"] == pytest.approx(0.75)
    assert errors["model_error"] == pytest.approx(0.5)


def test_group_importance_covers_every_family(model):
    importance = group_importance(model)
    assert set(importance["group"]) == set(FEATURE_GROUPS)
    assert importance["share"].sum() == pytest.approx(100)


@pytest.fixture
def by_station():
    """Build the errors of four stations, one per situation."""
    return pd.DataFrame(
        {
            "gare": ["AAA", "BBB", "CCC", "DDD"],
            "display_error": [2.0, 1.5, 0.5, 0.0],
            "model_error": [0.5, 1.4, 0.4, 0.0],
        }
    )


def test_classify_stations_measures_the_error_reduction(by_station):
    result = classify_stations(by_station, typical_error=1.0).set_index("gare")
    assert result.loc["AAA", "error_reduction"] == pytest.approx(75.0)
    assert result.loc["CCC", "error_reduction"] == pytest.approx(20.0)


def test_classify_stations_handles_a_station_without_error(by_station):
    result = classify_stations(by_station, typical_error=1.0).set_index("gare")
    assert result.loc["DDD", "error_reduction"] == 0.0


def test_classify_stations_gives_each_station_a_profile(by_station):
    result = classify_stations(by_station, typical_error=1.0).set_index("gare")
    assert result.loc["AAA", "profile"] == PREDICTABLE
    assert result.loc["BBB", "profile"] == UNPREDICTABLE
    assert result.loc["CCC", "profile"] == ACCURATE
    assert result.loc["DDD", "profile"] == ACCURATE
