"""Train the waiting-time model and save it for the app."""

from pathlib import Path

from sncf_waiting_time.data import load_data
from sncf_waiting_time.model import (
    overall_errors,
    predict_gap,
    save_model,
    score_predictions,
    split_by_day,
    station_usual_gap,
    train_model,
)

ROOT = Path(__file__).parent.parent
MODEL_PATH = ROOT / "models" / "waiting_time.json"


def main() -> None:
    """Train on the earlier days, evaluate on the latest and save the model."""
    data = load_data(ROOT / "data" / "x_train.csv.gz", ROOT / "data" / "y_train.csv.gz")
    training, test = split_by_day(data)
    stations = sorted(data["gare"].unique())

    model = train_model(training, stations)
    save_model(model, MODEL_PATH)

    scored = score_predictions(
        test, predict_gap(model, test), station_usual_gap(training)
    )
    errors = overall_errors(scored)
    print(f"Model saved to {MODEL_PATH}")
    print(f"Trained on {training['date'].nunique()} days, {len(training):,} stops")
    print(f"Evaluated on {test['date'].nunique()} days, {len(test):,} stops")
    print(f"Mean error of the screens:          {errors['display_error']:.3f} min")
    print(f"Mean error of a fixed correction:   {errors['correction_error']:.3f} min")
    print(f"Mean error of the model:            {errors['model_error']:.3f} min")


if __name__ == "__main__":
    main()
