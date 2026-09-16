# geosens/analysis/salmonella.py


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
# RISK CLASSIFICATION
# ============================================================

def classify_risk_level(
    percentile: float,
) -> str:
    """
    Convert percentile rank into a five-class relative risk level.
    """

    if percentile >= 80:
        return "Very High"

    if percentile >= 60:
        return "High"

    if percentile >= 40:
        return "Moderate"

    if percentile >= 20:
        return "Low"

    return "Very Low"


# ============================================================
# SALMONELLA RISK MAP
# ============================================================

def calculate_salmonella_risk_map(
    dataframe: pd.DataFrame,
    *,
    geography_column: str,
    cases_column: str,
    population_column: str,
) -> dict[str, Any]:
    """
    Calculate Salmonella risk for every geography.

    The function is geography-neutral.

    It calculates:

        cases / population * 100,000

    and ranks the resulting rate across the uploaded dataset.
    """

    # ========================================================
    # VALIDATE INPUT
    # ========================================================

    validate_dataframe(
        dataframe
    )

    validate_columns(
        dataframe,
        [
            geography_column,
            cases_column,
            population_column,
        ],
    )


    # ========================================================
    # WORKING DATA
    # ========================================================

    df = dataframe[
        [
            geography_column,
            cases_column,
            population_column,
        ]
    ].copy()


    # ========================================================
    # CLEAN VALUES
    # ========================================================

    df["_geography"] = (
        df[geography_column]
        .apply(
            clean_geography_value
        )
    )


    df["_cases"] = pd.to_numeric(
        df[cases_column],
        errors="coerce",
    )


    df["_population"] = pd.to_numeric(
        df[population_column],
        errors="coerce",
    )


    # ========================================================
    # VALID RECORDS
    # ========================================================

    valid_mask = (
            (df["_geography"] != "")
            & df["_cases"].notna()
            & df["_population"].notna()
            & (df["_cases"] >= 0)
            & (df["_population"] > 0)
        )


    df = df.loc[
        valid_mask
    ].copy()


    if df.empty:
        raise ValueError(
            "No valid analysis records were found. "
            "Check the selected geography, cases, and population fields."
        )


    # ========================================================
    # AGGREGATE DUPLICATE GEOGRAPHIES
    # ========================================================
    #
    # Cases are summed.
    # Population uses max() so duplicated population values
    # are not accidentally added together.
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
            "Expected one record per geography for the selected period. "
            f"Duplicate IDs found: {', '.join(examples)}. "
            "Aggregate cases and the corresponding population "
            "appropriately before uploading."
        )

    grouped = (
        df[["_geography", "_cases", "_population"]]
        .rename(
            columns={
                "_cases": "cases",
                "_population": "population",
            }
        )
        .reset_index(drop=True)
    )


    # ========================================================
    # RATE PER 100,000
    # ========================================================

    grouped["rate_per_100k"] = (
        grouped["cases"]
        /
        grouped["population"]
        *
        100000
    )

    rates = grouped["rate_per_100k"]

    if not np.isfinite(rates).all():
        raise ValueError(
            "Calculated rates contain nonfinite values. "
            "Check the cases and population data."
        )

    if len(grouped) < 2:
        raise ValueError(
            "Relative rate classification requires at least "
            "two valid geographies."
        )

    if rates.nunique() < 2:
        if (rates == 0).all():
            message = (
                "All analyzed geographies have zero reported cases. "
                "Relative rate categories cannot be assigned."
            )
        else:
            message = (
                "All analyzed geographies have the same reported "
                "case rate. Relative rate categories cannot be assigned."
            )

        raise ValueError(message)


    # ========================================================
    # PERCENTILE
    # ========================================================

    grouped["percentile"] = (
        grouped["rate_per_100k"]
        .rank(
            method="average",
            pct=True,
        )
        *
        100
    )


    # ========================================================
    # RISK CATEGORY
    # ========================================================

    grouped["risk_level"] = (
        grouped["percentile"]
        .apply(
            classify_risk_level
        )
    )


    risk_class_lookup = {
        "Very Low": 1,
        "Low": 2,
        "Moderate": 3,
        "High": 4,
        "Very High": 5,
    }


    grouped["risk_class"] = (
        grouped["risk_level"]
        .map(
            risk_class_lookup
        )
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
                        row["_geography"]
                    ),

                "cases":
                    int(
                        round(
                            float(
                                row["cases"]
                            )
                        )
                    ),

                "population":
                    int(
                        round(
                            float(
                                row["population"]
                            )
                        )
                    ),

                "rate_per_100k":
                    round(
                        float(
                            row["rate_per_100k"]
                        ),
                        2,
                    ),

                "percentile":
                    round(
                        float(
                            row["percentile"]
                        ),
                        2,
                    ),

                "risk_level":
                    str(
                        row["risk_level"]
                    ),

                "risk_class":
                    int(
                        row["risk_class"]
                    ),
            }
        )


    # ========================================================
    # SUMMARY
    # ========================================================

    rates = grouped[
        "rate_per_100k"
    ]


    highest_row = grouped.loc[
        rates.idxmax()
    ]


    lowest_row = grouped.loc[
        rates.idxmin()
    ]


    risk_counts = {
        level: int(
            (
                grouped[
                    "risk_level"
                ]
                ==
                level
            ).sum()
        )
        for level in [
            "Very Low",
            "Low",
            "Moderate",
            "High",
            "Very High",
        ]
    }


    total_cases = float(
        grouped[
            "cases"
        ].sum()
    )


    total_population = float(
        grouped[
            "population"
        ].sum()
    )


    summary = {

        "geographies_analyzed":
            int(
                len(grouped)
            ),

        "total_cases":
            int(
                round(
                    total_cases
                )
            ),

        "total_population":
            int(
                round(
                    total_population
                )
            ),

        "overall_rate_per_100k":
            round(
                float(
                    total_cases
                    /
                    total_population
                    *
                    100000
                ),
                2,
            ),

        "average_geography_rate":
            round(
                float(
                    rates.mean()
                ),
                2,
            ),

        "median_geography_rate":
            round(
                float(
                    rates.median()
                ),
                2,
            ),

        "highest_risk_geography":
            str(
                highest_row[
                    "_geography"
                ]
            ),

        "highest_rate_per_100k":
            round(
                float(
                    highest_row[
                        "rate_per_100k"
                    ]
                ),
                2,
            ),

        "lowest_risk_geography":
            str(
                lowest_row[
                    "_geography"
                ]
            ),

        "lowest_rate_per_100k":
            round(
                float(
                    lowest_row[
                        "rate_per_100k"
                    ]
                ),
                2,
            ),

        "risk_counts":
            risk_counts,
    }


    return {
        "records":
            records,

        "summary":
            summary,
    }


# ============================================================
# COUNTY SALMONELLA RISK
# ============================================================

def calculate_county_risk(
    dataframe: pd.DataFrame,
    county_name: str,
    state_name: str,
    *,
    county_column: str,
    state_column: str,
    cases_column: str,
    population_column: str,
) -> dict[str, Any]:
    """
    Calculate one county's relative Salmonella risk.

    This is retained for future county-level analysis.
    """

    # ========================================================
    # VALIDATE INPUT
    # ========================================================

    validate_dataframe(
        dataframe
    )

    validate_columns(
        dataframe,
        [
            county_column,
            state_column,
            cases_column,
            population_column,
        ],
    )


    df = dataframe.copy()


    # ========================================================
    # CLEAN COUNTY / STATE VALUES
    # ========================================================

    df["_county_clean"] = (
        df[county_column]
        .astype(str)
        .str.strip()
        .str.lower()
    )


    df["_state_clean"] = (
        df[state_column]
        .astype(str)
        .str.strip()
        .str.lower()
    )


    df["_county_without_suffix"] = (
        df["_county_clean"]
        .str.replace(
            r"\s+county$",
            "",
            regex=True,
        )
        .str.strip()
    )


    requested_county = (
        str(
            county_name
        )
        .strip()
        .lower()
    )


    requested_county_without_suffix = (
        requested_county
        .replace(
            " county",
            "",
        )
        .strip()
    )


    requested_state = (
        str(
            state_name
        )
        .strip()
        .lower()
    )


    # ========================================================
    # NUMERIC VALUES
    # ========================================================

    df["_cases"] = pd.to_numeric(
        df[cases_column],
        errors="coerce",
    )


    df["_population"] = pd.to_numeric(
        df[population_column],
        errors="coerce",
    )


    valid_mask = (
        np.isfinite(df["_cases"])
        & np.isfinite(df["_population"])
        & (df["_cases"] >= 0)
        & (df["_population"] > 0)
    )


    df = df.loc[
        valid_mask
    ].copy()


    if df.empty:
        raise ValueError(
            "No valid county records were found."
        )


    # ========================================================
    # FIND REQUESTED COUNTY
    # ========================================================

    county_mask = (
        (
            df["_county_clean"]
            ==
            requested_county
        )
        |
        (
            df["_county_without_suffix"]
            ==
            requested_county_without_suffix
        )
    )


    state_mask = (
        df["_state_clean"]
        ==
        requested_state
    )


    match = df.loc[
        county_mask
        &
        state_mask
    ]


    if match.empty:
        raise ValueError(
            f"County '{county_name}' in "
            f"state '{state_name}' was not found."
        )


    # ========================================================
    # CREATE COUNTY COMPARISON TABLE
    # ========================================================

    county_table = (
        df
        .groupby(
            [
                "_state_clean",
                "_county_without_suffix",
            ],
            as_index=False,
        )
        .agg(
            cases=(
                "_cases",
                "sum",
            ),

            population=(
                "_population",
                "max",
            ),
        )
    )


    county_table[
        "rate_per_100k"
    ] = (
        county_table[
            "cases"
        ]
        /
        county_table[
            "population"
        ]
        *
        100000
    )


    # ========================================================
    # SELECTED COUNTY VALUES
    # ========================================================

    county_cases = float(
        match[
            "_cases"
        ].sum()
    )


    county_population = float(
        match[
            "_population"
        ].max()
    )


    county_rate = (
        county_cases
        /
        county_population
        *
        100000
    )


    # ========================================================
    # NATIONAL PERCENTILE
    # ========================================================

    national_rates = county_table[
        "rate_per_100k"
    ]


    national_percentile = (
        (
            national_rates
            <=
            county_rate
        )
        .mean()
        *
        100
    )


    # ========================================================
    # STATE PERCENTILE
    # ========================================================

    state_table = county_table.loc[
        county_table[
            "_state_clean"
        ]
        ==
        requested_state
    ]


    state_percentile = (
        (
            state_table[
                "rate_per_100k"
            ]
            <=
            county_rate
        )
        .mean()
        *
        100
    )


    first_row = match.iloc[0]


    return {

        "county":
            str(
                first_row[
                    county_column
                ]
            ).strip(),

        "state":
            str(
                first_row[
                    state_column
                ]
            ).strip(),

        "cases":
            int(
                round(
                    county_cases
                )
            ),

        "population":
            int(
                round(
                    county_population
                )
            ),

        "rate_per_100k":
            round(
                county_rate,
                2,
            ),

        "national_percentile":
            round(
                national_percentile,
                2,
            ),

        "state_percentile":
            round(
                state_percentile,
                2,
            ),

        "risk_level":
            classify_risk_level(
                national_percentile
            ),
    }
