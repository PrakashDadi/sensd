# geosens/analysis/common.py

from typing import Any

import pandas as pd


def validate_dataframe(
    dataframe: pd.DataFrame,
) -> None:
    """
    Validate that a usable dataframe was supplied.
    """

    if dataframe is None or dataframe.empty:
        raise ValueError(
            "The analysis dataset is empty."
        )


def validate_columns(
    dataframe: pd.DataFrame,
    required_columns: list[str],
) -> None:
    """
    Validate that all required columns exist.
    """

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required fields: "
            + ", ".join(missing_columns)
        )


def clean_geography_value(value: Any) -> str:
    """Clean geography IDs while preserving case and leading zeros."""
    if pd.isna(value):
        return ""
    return str(value).strip()
