"""Tests for the data loading function."""

import pandas as pd
import pytest

from sncf_waiting_time.data import FEATURE_COLUMNS, TARGET_COLUMN, load_data


@pytest.fixture
def raw_files(tmp_path):
    """Write a small features file and its target file, as the raw data."""
    features = pd.DataFrame(
        {
            "Unnamed: 0.1": [0, 1, 2],
            "Unnamed: 0": [0, 1, 2],
            "train": ["AAA", "AAA", "BBB"],
            "gare": ["KYF", "JLR", "KYF"],
            "date": ["2023-04-03", "2023-04-03", "2023-04-04"],
            "arret": [8, 9, 8],
            "p2q0": [0.0, 1.0, -1.0],
            "p3q0": [0.0, 0.0, -2.0],
            "p4q0": [1.0, 0.0, 0.0],
            "p0q2": [-3.0, 1.0, 0.0],
            "p0q3": [-1.0, 0.0, 2.0],
            "p0q4": [-2.0, 1.0, 0.0],
        }
    )
    target = pd.DataFrame({"Unnamed: 0": [0, 1, 2], "p0q0": [-1.0, 0.0, 2.0]})
    x_path = tmp_path / "x.csv"
    y_path = tmp_path / "y.csv"
    features.to_csv(x_path, index=False)
    target.to_csv(y_path, index=False)
    return x_path, y_path


def test_load_data_columns(raw_files):
    x_path, y_path = raw_files
    data = load_data(x_path, y_path)
    assert list(data.columns) == FEATURE_COLUMNS + [TARGET_COLUMN]


def test_load_data_keeps_all_rows(raw_files):
    x_path, y_path = raw_files
    data = load_data(x_path, y_path)
    assert len(data) == 3


def test_load_data_matches_target_to_stop(raw_files):
    x_path, y_path = raw_files
    data = load_data(x_path, y_path)
    assert data["p0q0"].tolist() == [-1.0, 0.0, 2.0]


def test_load_data_parses_date(raw_files):
    x_path, y_path = raw_files
    data = load_data(x_path, y_path)
    assert data["date"].iloc[0] == pd.Timestamp(2023, 4, 3)


def test_load_data_missing_column(raw_files):
    x_path, y_path = raw_files
    pd.read_csv(x_path).drop(columns="gare").to_csv(x_path, index=False)
    with pytest.raises(ValueError):
        load_data(x_path, y_path)


def test_load_data_different_lengths(raw_files):
    x_path, y_path = raw_files
    pd.read_csv(y_path).iloc[:2].to_csv(y_path, index=False)
    with pytest.raises(ValueError):
        load_data(x_path, y_path)


def test_load_data_missing_target(raw_files):
    x_path, y_path = raw_files
    pd.read_csv(y_path).rename(columns={"p0q0": "other"}).to_csv(y_path, index=False)
    with pytest.raises(ValueError):
        load_data(x_path, y_path)
