"""Train, save and evaluate the model predicting the waiting-time gap."""

from pathlib import Path

import pandas as pd
import xgboost as xgb

from sncf_waiting_time.data import TARGET_COLUMN
from sncf_waiting_time.features import FEATURE_GROUPS, build_features

TEST_DAYS = 18
BOOSTING_ROUNDS = 300
PARAMETERS = {
    "objective": "reg:absoluteerror",
    "eta": 0.1,
    "max_depth": 6,
    "min_child_weight": 5,
    "gamma": 0.2,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "lambda": 1.0,
    "tree_method": "hist",
    "seed": 0,
}
PREDICTABLE = "Predictable gap: correct the display"
UNPREDICTABLE = "Unpredictable gap: look at operations"
ACCURATE = "Screens already close to reality"
MIN_ERROR_REDUCTION = 30.0


def split_by_day(
    data: pd.DataFrame, test_days: int = TEST_DAYS
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Set the most recent days aside to evaluate the model.

    Whole days are kept together: the model is evaluated on days it has
    never seen, as it would be in real use.

    :param data: train stops, one row per stop
    :param test_days: number of most recent days to set aside
    :return: the stops used for training, then the stops set aside
    """
    days = sorted(data["date"].unique())
    if not 0 < test_days < len(days):
        raise ValueError(
            f"Cannot set {test_days} day(s) aside out of {len(days)} day(s)"
        )
    first_test_day = days[-test_days]
    is_test = data["date"] >= first_test_day
    return data[~is_test], data[is_test]


def train_model(
    data: pd.DataFrame, stations: list[str], rounds: int = BOOSTING_ROUNDS
) -> xgb.Booster:
    """
    Train the model to predict the waiting-time gap.

    The list of stations is stored inside the model, so that predictions
    always encode the stations the way training did.

    :param data: train stops used for training, with the target
    :param stations: every station code, in a fixed order
    :param rounds: number of trees to build
    :return: the trained model
    """
    features = build_features(data, stations)
    matrix = xgb.DMatrix(features, label=data[TARGET_COLUMN], enable_categorical=True)
    model = xgb.train(PARAMETERS, matrix, num_boost_round=rounds)
    model.set_attr(stations=",".join(stations))
    return model


def predict_gap(model: xgb.Booster, data: pd.DataFrame) -> pd.Series:
    """
    Predict the waiting-time gap of each train stop.

    :param model: the trained model
    :param data: train stops, one row per stop
    :return: the predicted gap in minutes, one value per stop
    """
    stations = model.attr("stations").split(",")
    features = build_features(data, stations)
    matrix = xgb.DMatrix(features, enable_categorical=True)
    return pd.Series(model.predict(matrix), index=data.index, name="prediction")


def save_model(model: xgb.Booster, path: str | Path) -> None:
    """
    Save the trained model to a file.

    :param model: the trained model
    :param path: file to write, ending in .json
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    model.save_model(path)


def load_model(path: str | Path) -> xgb.Booster:
    """
    Load a trained model from a file.

    :param path: file written by save_model
    :return: the trained model
    """
    model = xgb.Booster()
    model.load_model(path)
    return model


def station_usual_gap(data: pd.DataFrame) -> pd.Series:
    """
    Find the usual gap of each station, as its median gap.

    This is the simplest possible correction: shift the announced wait of a
    station by its usual gap, without any model.

    :param data: train stops used for training, with the target
    :return: the usual gap in minutes, one value per station
    """
    return data.groupby("gare")[TARGET_COLUMN].median()


def score_predictions(
    data: pd.DataFrame, predictions: pd.Series, usual_gap: pd.Series
) -> pd.DataFrame:
    """
    Measure the error of the screens, of a fixed correction and of the model.

    The screens announce the planned wait, so their error is the gap
    itself. Predictions are rounded, as screens show whole minutes.

    :param data: train stops set aside, with the target
    :param predictions: gap predicted by the model for each stop
    :param usual_gap: usual gap of each station
    :return: train stops with one error column per method, in minutes
    """
    actual = data[TARGET_COLUMN]
    correction = data["gare"].map(usual_gap).fillna(0)
    return data.assign(
        display_error=actual.abs(),
        correction_error=(actual - correction).abs(),
        model_error=(actual - predictions.round()).abs(),
    )


def errors_by_station(scored: pd.DataFrame) -> pd.DataFrame:
    """
    Average the errors of each method, station by station.

    :param scored: train stops with the error columns of score_predictions
    :return: one row per station, with its stops, mean gap and mean errors
    """
    summary = scored.groupby("gare").agg(
        stops=(TARGET_COLUMN, "size"),
        mean_gap=(TARGET_COLUMN, "mean"),
        display_error=("display_error", "mean"),
        correction_error=("correction_error", "mean"),
        model_error=("model_error", "mean"),
    )
    return summary.reset_index()


def overall_errors(scored: pd.DataFrame) -> dict:
    """
    Average the errors of each method over all the train stops.

    :param scored: train stops with the error columns of score_predictions
    :return: mean error in minutes of the screens, the correction and the model
    """
    return {
        "display_error": float(scored["display_error"].mean()),
        "correction_error": float(scored["correction_error"].mean()),
        "model_error": float(scored["model_error"].mean()),
    }


def group_importance(model: xgb.Booster) -> pd.DataFrame:
    """
    Measure how much each family of variables contributes to the model.

    :param model: the trained model
    :return: one row per family of variables, with its share in percent
    """
    gains = model.get_score(importance_type="total_gain")
    totals = {
        group: sum(gains.get(name, 0.0) for name in names)
        for group, names in FEATURE_GROUPS.items()
    }
    total = sum(totals.values())
    shares = [
        {"group": group, "share": 100 * gain / total if total else 0.0}
        for group, gain in totals.items()
    ]
    return pd.DataFrame(shares).sort_values("share", ascending=False, ignore_index=True)


def classify_stations(
    by_station: pd.DataFrame,
    typical_error: float,
    min_reduction: float = MIN_ERROR_REDUCTION,
) -> pd.DataFrame:
    """
    Tell apart the stations a model can fix from those it cannot.

    A station whose screens are no worse than usual needs no action. Among
    the others, the gap is predictable when the model removes a large part
    of the error, and unpredictable otherwise.

    :param by_station: one row per station, as returned by errors_by_station
    :param typical_error: mean error of the screens over all stations
    :param min_reduction: share of the error, in percent, the model must
        remove for the gap to count as predictable
    :return: the stations with their error reduction in percent and profile
    """
    display_error = by_station["display_error"]
    reduction = 100 * (1 - by_station["model_error"] / display_error)
    reduction = reduction.where(display_error > 0, 0.0)

    profile = pd.Series(UNPREDICTABLE, index=by_station.index)
    profile = profile.where(reduction < min_reduction, PREDICTABLE)
    profile = profile.where(display_error > typical_error, ACCURATE)
    return by_station.assign(error_reduction=reduction, profile=profile)
