# geosens/analysis/bivariate.py

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .common import (
    clean_geography_value,
    validate_columns,
    validate_dataframe,
)


# ============================================================
# BIVARIATE HELPERS
# ============================================================

def _classify_tertiles(
    series: pd.Series,
) -> tuple[pd.Series, dict[str, float]]:
    """Assign classes using the same boundaries reported in the output."""
    if series.empty or series.notna().sum() < 3:
        raise ValueError(
            "At least three valid values are required "
            "for bivariate classification."
        )

    quantiles = series.quantile([1 / 3, 2 / 3])
    low_upper = float(quantiles.loc[1 / 3])
    medium_upper = float(quantiles.loc[2 / 3])

    classes = pd.Series(
        np.select(
            [
                series <= low_upper,
                series <= medium_upper,
            ],
            [1, 2],
            default=3,
        ),
        index=series.index,
        dtype="int64",
    )

    breaks = {
        "low_upper": low_upper,
        "medium_upper": medium_upper,
    }

    return classes, breaks

def _bivariate_level_label(
    class_value: int,
) -> str:
    """
    Convert numeric bivariate class into a readable level.
    """

    mapping = {
        1: "Low",
        2: "Medium",
        3: "High",
    }


    return mapping.get(
        int(class_value),
        "Unknown",
    )


# ============================================================
# BIVARIATE ANALYSIS
# ============================================================

def calculate_bivariate_map(
    dataframe: pd.DataFrame,
    *,
    geography_column: str,
    x_column: str,
    y_column: str,
) -> dict[str, Any]:
    """
    Create a generic 3 x 3 bivariate classification.

    Variable X and Variable Y are each classified into:

        Low
        Medium
        High

    The two classifications are then combined into one
    of nine bivariate classes.

    Examples
    --------

    Salmonella Rate × Food Insecurity

    Salmonella Rate × Social Vulnerability

    Food Insecurity × Social Vulnerability

    The function does not assume what X or Y represent.
    """

    # ========================================================
    # VALIDATION
    # ========================================================

    validate_dataframe(
        dataframe
    )


    validate_columns(
        dataframe,
        [
            geography_column,
            x_column,
            y_column,
        ],
    )


    if x_column == y_column:
        raise ValueError(
            "Variable 1 and Variable 2 must be different fields."
        )


    # ========================================================
    # WORKING DATA
    # ========================================================

    df = dataframe[
        [
            geography_column,
            x_column,
            y_column,
        ]
    ].copy()


    df["_geography"] = (
        df[geography_column]
        .apply(
            clean_geography_value
        )
    )


    df["_x"] = pd.to_numeric(
        df[x_column],
        errors="coerce",
    )


    df["_y"] = pd.to_numeric(
        df[y_column],
        errors="coerce",
    )


    # ========================================================
    # VALID RECORDS
    # ========================================================

    valid_mask = (
        (df["_geography"] != "")
        & df["_x"].notna()
        & df["_y"].notna()
        & np.isfinite(df["_x"])
        & np.isfinite(df["_y"])
    )


    df = df.loc[
        valid_mask
    ].copy()


    if df.empty:
        raise ValueError(
            "No valid records were found for "
            "the selected bivariate fields."
        )


    # ========================================================
    # AGGREGATE DUPLICATE GEOGRAPHIES
    # ========================================================
    #
    # For generic numeric variables, mean is used for duplicate
    # geographies instead of summing values.
    # ========================================================

    duplicate_mask = df["_geography"].duplicated(keep=False)

    if duplicate_mask.any():
        examples = (
            df.loc[duplicate_mask, "_geography"]
            .drop_duplicates()
            .head(5)
            .tolist()
        )

        raise ValueError(
            "The geography field must uniquely identify each record. "
            f"Duplicate IDs found: {', '.join(examples)}. "
            "Aggregate repeated records using an appropriate method "
            "before uploading."
        )

    grouped = (
        df[["_geography", "_x", "_y"]]
        .rename(
            columns={
                "_x": "x_value",
                "_y": "y_value",
            }
        )
        .reset_index(drop=True)
    )


    if len(grouped) < 3:
        raise ValueError(
            "Bivariate analysis requires at least "
            "three valid geographies."
        )


    # ========================================================
    # CHECK VARIABLE VARIATION
    # ========================================================

    if (
        grouped[
            "x_value"
        ].nunique()
        <
        2
    ):
        raise ValueError(
            f"Variable '{x_column}' does not contain "
            "enough variation for bivariate analysis."
        )


    if (
        grouped[
            "y_value"
        ].nunique()
        <
        2
    ):
        raise ValueError(
            f"Variable '{y_column}' does not contain "
            "enough variation for bivariate analysis."
        )


    # ========================================================
    # CLASSIFY VARIABLE X
    # ========================================================

    (
        grouped["x_class"],
        x_breaks,
    ) = _classify_tertiles(
        grouped[
            "x_value"
        ]
    )


    # ========================================================
    # CLASSIFY VARIABLE Y
    # ========================================================

    (
        grouped["y_class"],
        y_breaks,
    ) = _classify_tertiles(
        grouped[
            "y_value"
        ]
    )


    # ========================================================
    # READABLE CLASS LABELS
    # ========================================================

    grouped["x_level"] = (
        grouped[
            "x_class"
        ]
        .apply(
            _bivariate_level_label
        )
    )


    grouped["y_level"] = (
        grouped[
            "y_class"
        ]
        .apply(
            _bivariate_level_label
        )
    )


    # ========================================================
    # BIVARIATE CLASS CODE
    # ========================================================
    #
    # x1y1 = Low X / Low Y
    # x2y1 = Medium X / Low Y
    # x3y1 = High X / Low Y
    #
    # x1y2 = Low X / Medium Y
    # x2y2 = Medium X / Medium Y
    # x3y2 = High X / Medium Y
    #
    # x1y3 = Low X / High Y
    # x2y3 = Medium X / High Y
    # x3y3 = High X / High Y
    # ========================================================

    grouped[
        "bivariate_class"
    ] = (
        "x"
        +
        grouped[
            "x_class"
        ].astype(str)
        +
        "y"
        +
        grouped[
            "y_class"
        ].astype(str)
    )


    # ========================================================
    # READABLE BIVARIATE LABEL
    # ========================================================

    grouped[
        "bivariate_label"
    ] = (
        grouped[
            "x_level"
        ]
        +
        " X / "
        +
        grouped[
            "y_level"
        ]
        +
        " Y"
    )


    # ========================================================
    # NUMERIC CLASS
    # ========================================================
    #
    #       X
    #       1  2  3
    #
    # Y 1   1  2  3
    #   2   4  5  6
    #   3   7  8  9
    # ========================================================

    grouped[
        "bivariate_class_number"
    ] = (
        (
            grouped[
                "y_class"
            ]
            -
            1
        )
        *
        3
        +
        grouped[
            "x_class"
        ]
    )


    # ========================================================
    # OUTPUT RECORDS
    # ========================================================

    records = []


    for _, row in grouped.iterrows():

        records.append(
            {
                "geography":
                    str(
                        row[
                            "_geography"
                        ]
                    ),

                "x_value":
                    round(
                        float(
                            row[
                                "x_value"
                            ]
                        ),
                        6,
                    ),

                "y_value":
                    round(
                        float(
                            row[
                                "y_value"
                            ]
                        ),
                        6,
                    ),

                "x_class":
                    int(
                        row[
                            "x_class"
                        ]
                    ),

                "y_class":
                    int(
                        row[
                            "y_class"
                        ]
                    ),

                "x_level":
                    str(
                        row[
                            "x_level"
                        ]
                    ),

                "y_level":
                    str(
                        row[
                            "y_level"
                        ]
                    ),

                "bivariate_class":
                    str(
                        row[
                            "bivariate_class"
                        ]
                    ),

                "bivariate_class_number":
                    int(
                        row[
                            "bivariate_class_number"
                        ]
                    ),

                "bivariate_label":
                    str(
                        row[
                            "bivariate_label"
                        ]
                    ),
            }
        )


    # ========================================================
    # CLASS COUNTS
    # ========================================================

    all_classes = [

        "x1y1",
        "x2y1",
        "x3y1",

        "x1y2",
        "x2y2",
        "x3y2",

        "x1y3",
        "x2y3",
        "x3y3",
    ]


    observed_counts = (
        grouped[
            "bivariate_class"
        ]
        .value_counts()
        .to_dict()
    )


    class_counts = {

        class_name:
            int(
                observed_counts.get(
                    class_name,
                    0,
                )
            )

        for class_name
        in all_classes
    }


    # ========================================================
    # HIGH-HIGH / LOW-LOW AREAS
    # ========================================================

    high_high_geographies = (
        grouped.loc[
            grouped[
                "bivariate_class"
            ]
            ==
            "x3y3",
            "_geography",
        ]
        .astype(str)
        .tolist()
    )


    low_low_geographies = (
        grouped.loc[
            grouped[
                "bivariate_class"
            ]
            ==
            "x1y1",
            "_geography",
        ]
        .astype(str)
        .tolist()
    )


    # ========================================================
    # PEARSON CORRELATION
    # ========================================================
    #
    # This describes the non-spatial relationship between X
    # and Y. It is NOT Moran's I or another spatial statistic.
    # ========================================================

    correlation = (
        grouped[
            [
                "x_value",
                "y_value",
            ]
        ]
        .corr(
            method="pearson"
        )
        .iloc[
            0,
            1
        ]
    )


    if pd.isna(
        correlation
    ):

        correlation_value = None

    else:

        correlation_value = round(
            float(
                correlation
            ),
            4,
        )


    # ========================================================
    # SUMMARY
    # ========================================================

    summary = {

        "geographies_analyzed":
            int(
                len(
                    grouped
                )
            ),

        "x_field":
            x_column,

        "y_field":
            y_column,

        "x_min":
            round(
                float(
                    grouped[
                        "x_value"
                    ].min()
                ),
                6,
            ),

        "x_max":
            round(
                float(
                    grouped[
                        "x_value"
                    ].max()
                ),
                6,
            ),

        "y_min":
            round(
                float(
                    grouped[
                        "y_value"
                    ].min()
                ),
                6,
            ),

        "y_max":
            round(
                float(
                    grouped[
                        "y_value"
                    ].max()
                ),
                6,
            ),

        "x_breaks":
            x_breaks,

        "y_breaks":
            y_breaks,

        "class_counts":
            class_counts,

        "high_high_count":
            int(
                len(
                    high_high_geographies
                )
            ),

        "high_high_geographies":
            high_high_geographies,

        "low_low_count":
            int(
                len(
                    low_low_geographies
                )
            ),

        "low_low_geographies":
            low_low_geographies,

        "pearson_correlation":
            correlation_value,
    }


    return {

        "records":
            records,

        "summary":
            summary,
    }
