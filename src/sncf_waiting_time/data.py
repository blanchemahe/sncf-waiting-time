"""Load the SNCF platform waiting-time data."""

from pathlib import Path

import pandas as pd

INDEX_COLUMN = "Unnamed: 0"
TARGET_COLUMN = "p0q0"
FEATURE_COLUMNS = [
    "train",
    "gare",
    "date",
    "arret",
    "p2q0",
    "p3q0",
    "p4q0",
    "p0q2",
    "p0q3",
    "p0q4",
]


def load_data(x_path: str | Path, y_path: str | Path) -> pd.DataFrame:
    """
    Load the features and the target and merge them into one table.

    Each row is one train stop. The index columns of the raw files are
    dropped and the date is converted to a datetime.

    :param x_path: path to the CSV file of features
    :param y_path: path to the CSV file of the target
    :return: one row per train stop, with features and target
    """
    features = pd.read_csv(x_path)
    target = pd.read_csv(y_path)

    missing = set(FEATURE_COLUMNS + [INDEX_COLUMN]) - set(features.columns)
    if missing:
        raise ValueError(f"Missing columns in features file: {sorted(missing)}")
    if TARGET_COLUMN not in target.columns:
        raise ValueError(f"Missing column in target file: {TARGET_COLUMN}")
    if len(features) != len(target):
        raise ValueError(
            f"Features and target have different lengths: "
            f"{len(features)} and {len(target)}"
        )

    data = features.merge(target, on=INDEX_COLUMN, validate="one_to_one")
    data = data[FEATURE_COLUMNS + [TARGET_COLUMN]]
    data["date"] = pd.to_datetime(data["date"], format="%Y-%m-%d")
    return data
