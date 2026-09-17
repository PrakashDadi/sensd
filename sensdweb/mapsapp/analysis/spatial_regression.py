"""
SENSD Spatial Regression Analysis
=================================

Version 1
---------
OLS Regression + Spatial Diagnostics

Purpose
-------
This module evaluates relationships between a dependent variable Y
and one or more independent variables X while checking whether
spatial dependence remains in the regression residuals.

The initial SENSD workflow is:

    1. Fit OLS regression
    2. Examine model fit and coefficients
    3. Test residual spatial autocorrelation
    4. Run Lagrange Multiplier diagnostics for:
       - Spatial Error dependence
       - Robust Spatial Error dependence
       - Spatial Lag dependence
       - Robust Spatial Lag dependence

This module does NOT automatically fit Spatial Lag or Spatial Error
models yet. Those models should be added as a later stage after the
OLS diagnostics are working and validated.

Spatial weights
---------------
SENSD uses:

    Queen contiguity
    rook=False

and:

    row-standardized weights

This keeps the spatial-neighborhood definition consistent with the
existing SENSD Local Moran and Spatial Association analyses.

PySAL implementation
---------------------
The analysis uses the public PySAL/spreg API:

    spreg.OLS
    spreg.LMtests
    spreg.MoranRes

Official implementation:
https://github.com/pysal/spreg

Official documentation:
https://pysal.org/spreg/

Methodological background
-------------------------
Anselin, L. (1988).
Spatial Econometrics: Methods and Models.
Kluwer Academic Publishers.

Anselin, L., Bera, A. K., Florax, R., & Yoon, M. J. (1996).
Simple diagnostic tests for spatial dependence.
Regional Science and Urban Economics, 26(1), 77-104.

Interpretation note
-------------------
OLS coefficient associations should not automatically be interpreted
as causal effects.

The spatial diagnostics assess whether residual spatial dependence
remains after controlling for the selected explanatory variables.

The LM tests help diagnose forms of spatial dependence but should not
be treated as an automatic proof that one spatial model is the only
correct specification.
"""

from __future__ import annotations

import math
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

import spreg
from libpysal import graph


# ============================================================
# DEFAULT SETTINGS
# ============================================================

DEFAULT_SIGNIFICANCE_LEVEL = 0.05


# ============================================================
# JSON-SAFE HELPER
# ============================================================

def _json_safe(value: Any) -> Any:
    """
    Convert NumPy / pandas scalar values into JSON-safe Python values.
    """

    if value is None:
        return None

    if isinstance(value, (np.bool_, bool)):
        return bool(value)

    if isinstance(value, (np.integer, int)):
        return int(value)

    if isinstance(value, (np.floating, float)):
        numeric_value = float(value)

        if not math.isfinite(numeric_value):
            return None

        return numeric_value

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value


# ============================================================
# GEOGRAPHY CLEANING
# ============================================================

def _clean_geography_value(value: Any) -> str:
    """
    Convert a geography identifier into a clean string.
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    return str(value).strip()


# ============================================================
# PREPARE GEODATAFRAME
# ============================================================

def prepare_spatial_regression_geodataframe(
    geojson_data: dict,
    geography_column: str,
    dependent_column: str,
    independent_columns: list[str],
) -> gpd.GeoDataFrame:
    """
    Validate and prepare polygon data for spatial regression.

    Requirements
    ------------
    - GeoJSON FeatureCollection
    - Polygon / MultiPolygon geometry
    - unique geography identifier
    - numeric dependent variable
    - one or more numeric independent variables
    - no missing/non-finite values in model variables
    - sufficient observations relative to number of predictors
    """

    if not isinstance(geojson_data, dict):
        raise ValueError(
            "GeoJSON data must be a valid object."
        )

    if geojson_data.get("type") != "FeatureCollection":
        raise ValueError(
            "Spatial Regression Analysis requires a "
            "GeoJSON FeatureCollection."
        )

    features = geojson_data.get("features") or []

    if not features:
        raise ValueError(
            "The GeoJSON dataset contains no features."
        )

    if not geography_column:
        raise ValueError(
            "Geography Field is required."
        )

    if not dependent_column:
        raise ValueError(
            "Dependent Variable is required."
        )

    if not independent_columns:
        raise ValueError(
            "Select at least one independent variable."
        )

    independent_columns = [
        str(column).strip()
        for column in independent_columns
        if str(column).strip()
    ]

    if not independent_columns:
        raise ValueError(
            "Select at least one independent variable."
        )

    if dependent_column in independent_columns:
        raise ValueError(
            "The dependent variable cannot also be used as an "
            "independent variable."
        )

    if len(set(independent_columns)) != len(independent_columns):
        raise ValueError(
            "Independent variables must be unique."
        )

    try:
        gdf = gpd.GeoDataFrame.from_features(
            features
        )

    except Exception as exc:
        raise ValueError(
            "The uploaded GeoJSON could not be converted "
            "to a GeoDataFrame."
        ) from exc

    if gdf.empty:
        raise ValueError(
            "The uploaded spatial dataset is empty."
        )

    required_columns = [
        geography_column,
        dependent_column,
        *independent_columns,
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in gdf.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required fields: "
            + ", ".join(missing_columns)
        )

    if "geometry" not in gdf.columns:
        raise ValueError(
            "The uploaded dataset does not contain geometry."
        )

    # --------------------------------------------------------
    # Remove missing geometry
    # --------------------------------------------------------

    gdf = gdf[
        gdf.geometry.notna()
    ].copy()

    if gdf.empty:
        raise ValueError(
            "No valid geometries were found."
        )

    # --------------------------------------------------------
    # Polygon geometry requirement
    # --------------------------------------------------------

    geometry_types = set(
        gdf.geometry
        .geom_type
        .dropna()
        .unique()
    )

    allowed_geometry_types = {
        "Polygon",
        "MultiPolygon",
    }

    unsupported_types = (
        geometry_types
        - allowed_geometry_types
    )

    if unsupported_types:
        raise ValueError(
            "Spatial Regression Analysis currently requires "
            "Polygon or MultiPolygon geometry. Unsupported "
            "geometry types found: "
            + ", ".join(
                sorted(
                    unsupported_types
                )
            )
        )

    # --------------------------------------------------------
    # Repair invalid polygons where possible
    # --------------------------------------------------------

    invalid_mask = ~gdf.geometry.is_valid

    if invalid_mask.any():

        try:
            gdf.loc[
                invalid_mask,
                "geometry",
            ] = (
                gdf.loc[
                    invalid_mask,
                    "geometry",
                ]
                .make_valid()
            )

        except Exception:
            pass

    # Recheck geometry type and emptiness after repair.
    usable_geometry = (
        gdf.geometry.notna()
        & ~gdf.geometry.is_empty
        & gdf.geometry.is_valid
        & gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    )

    gdf = gdf.loc[usable_geometry].copy()

    if gdf.empty:
        raise ValueError(
            "No valid polygon geometries remain after validation."
        )

    # --------------------------------------------------------
    # Geography identifier
    # --------------------------------------------------------

    gdf[
        geography_column
    ] = (
        gdf[
            geography_column
        ]
        .map(
            _clean_geography_value
        )
    )

    gdf = gdf[
        gdf[
            geography_column
        ]
        != ""
    ].copy()

    if gdf.empty:
        raise ValueError(
            "No valid geography identifiers were found."
        )

    duplicate_mask = (
        gdf[
            geography_column
        ]
        .duplicated(
            keep=False
        )
    )

    if duplicate_mask.any():

        examples = (
            gdf.loc[
                duplicate_mask,
                geography_column,
            ]
            .drop_duplicates()
            .head(5)
            .tolist()
        )

        raise ValueError(
            "Geography Field must uniquely identify each polygon. "
            "Duplicate values were found"
            + (
                ": "
                + ", ".join(examples)
                if examples
                else "."
            )
        )

    # --------------------------------------------------------
    # Numeric variables
    # --------------------------------------------------------

    numeric_columns = [
        dependent_column,
        *independent_columns,
    ]

    for column in numeric_columns:
        gdf[column] = pd.to_numeric(
            gdf[column],
            errors="coerce",
        )

    finite_mask = np.ones(
        len(gdf),
        dtype=bool,
    )

    for column in numeric_columns:
        finite_mask &= np.isfinite(
            gdf[column].to_numpy(
                dtype=float
            )
        )

    gdf = gdf[
        finite_mask
    ].copy()

    if gdf.empty:
        raise ValueError(
            "No observations contain valid numeric values for all "
            "selected regression variables."
        )

    # --------------------------------------------------------
    # Variation checks
    # --------------------------------------------------------

    if (
        gdf[
            dependent_column
        ]
        .nunique(
            dropna=True
        )
        < 2
    ):
        raise ValueError(
            f"Dependent variable ({dependent_column}) must contain "
            "at least two distinct values."
        )

    for column in independent_columns:

        if (
            gdf[column]
            .nunique(
                dropna=True
            )
            < 2
        ):
            raise ValueError(
                f"Independent variable ({column}) must contain at "
                "least two distinct values."
            )

    # --------------------------------------------------------
    # Minimum sample-size check
    # --------------------------------------------------------
    #
    # OLS contains:
    #
    #     intercept + k predictors
    #
    # We require more observations than parameters and impose a
    # practical minimum beyond that.
    # --------------------------------------------------------

    predictor_count = len(
        independent_columns
    )

    parameter_count = (
        predictor_count
        + 1
    )

    minimum_observations = max(
        parameter_count + 2,
        5,
    )

    if len(gdf) < minimum_observations:
        raise ValueError(
            "Spatial Regression Analysis requires at least "
            f"{minimum_observations} valid observations for the "
            f"selected {predictor_count} independent variable(s)."
        )

    # --------------------------------------------------------
    # Reset index
    # --------------------------------------------------------

    gdf = gdf.reset_index(
        drop=True
    )

    return gdf


# ============================================================
# GRAPH -> WEIGHTS CONVERSION
# ============================================================

def _build_spatial_weights(
    gdf: gpd.GeoDataFrame,
):
    """
    Build Queen-contiguity, row-standardized spatial weights.

    The other SENSD spatial-analysis modules use libpysal Graph.

    PySAL/spreg diagnostics expect a classic libpysal weights object
    exposing properties such as n, s0, and sparse.

    Graph.to_W() is therefore used when available.
    """

    weights_graph = (
        graph.Graph
        .build_contiguity(
            gdf,
            rook=False,
        )
        .transform(
            "r"
        )
    )

    try:
        weights = (
            weights_graph
            .to_W()
        )

    except Exception as exc:
        raise ValueError(
            "Could not convert Queen-contiguity graph into "
            "spatial weights required for regression diagnostics."
        ) from exc

    weights.transform = "r"

    return (
        weights_graph,
        weights,
    )


# ============================================================
# NEIGHBOR COUNTS
# ============================================================

def _get_neighbor_counts(weights_graph, observation_count):
    """Return validated neighbor counts in GeoDataFrame row order."""
    try:
        cardinalities = weights_graph.cardinalities

        if not isinstance(cardinalities, pd.Series):
            raise ValueError("Unexpected neighbor-count format.")

        if (
            not cardinalities.index.is_unique
            or len(cardinalities) != observation_count
        ):
            raise ValueError("Neighbor counts do not match the dataset.")

        counts = cardinalities.reindex(
            pd.RangeIndex(observation_count)
        ).to_numpy(dtype=float)

        if (
            not np.isfinite(counts).all()
            or (counts < 0).any()
            or (counts != np.floor(counts)).any()
        ):
            raise ValueError(
                "Neighbor counts contain invalid or missing values."
            )

        return counts.astype(int)

    except Exception as exc:
        raise ValueError(
            f"Could not retrieve valid spatial neighbor counts: {exc}"
        ) from exc

# ============================================================
# TEST RESULT HELPER
# ============================================================

def _test_result(
    result,
    significance_level: float,
) -> dict:
    """
    Convert a PySAL LM diagnostic tuple into a JSON-safe dictionary.

    Expected form:
        (statistic, p_value)
    """

    if (
        result is None
        or len(result) < 2
    ):
        return {
            "statistic": None,
            "p_value": None,
            "significant": False,
        }

    statistic = _json_safe(
        result[0]
    )

    p_value = _json_safe(
        result[1]
    )

    significant = bool(
        p_value is not None
        and float(p_value)
        <= significance_level
    )

    return {
        "statistic": statistic,
        "p_value": p_value,
        "significant": significant,
    }


# ============================================================
# MODEL DIAGNOSTIC INTERPRETATION
# ============================================================

def _diagnostic_interpretation(
    *,
    residual_moran_p: float | None,
    lm_error: dict,
    robust_lm_error: dict,
    lm_lag: dict,
    robust_lm_lag: dict,
    significance_level: float,
) -> dict:
    """
    Produce a cautious interpretation of spatial diagnostics.

    This intentionally avoids automatically declaring a single
    "correct" spatial model.
    """
    # Missing diagnostic results do not mean spatial dependence is absent.
    required_values = [
        residual_moran_p,
    ]

    for test in (
        lm_error,
        robust_lm_error,
        lm_lag,
        robust_lm_lag,
    ):
        required_values.extend(
            [
                test.get("statistic"),
                test.get("p_value"),
            ]
        )

    if any(
        value is None or not math.isfinite(float(value))
        for value in required_values
    ):
        return {
            "residual_spatial_dependence": None,
            "model_indication": "Diagnostics Unavailable",
            "interpretation": (
                "One or more spatial diagnostics could not be "
                "calculated reliably. Available individual test "
                "results are reported separately, but an overall "
                "spatial model recommendation cannot be made."
            ),
        }

    residual_spatial_dependence = bool(
        residual_moran_p is not None
        and float(
            residual_moran_p
        )
        <= significance_level
    )

    robust_error_sig = bool(
        robust_lm_error[
            "significant"
        ]
    )

    robust_lag_sig = bool(
        robust_lm_lag[
            "significant"
        ]
    )

    lm_error_sig = bool(
        lm_error[
            "significant"
        ]
    )

    lm_lag_sig = bool(
        lm_lag[
            "significant"
        ]
    )

    if (
        robust_error_sig
        and not robust_lag_sig
    ):

        indication = (
            "Spatial Error"
        )

        interpretation = (
            "The robust LM diagnostics provide stronger evidence "
            "for spatial dependence in the regression error process. "
            "A Spatial Error specification may be considered in the "
            "next modeling stage."
        )

    elif (
        robust_lag_sig
        and not robust_error_sig
    ):

        indication = (
            "Spatial Lag"
        )

        interpretation = (
            "The robust LM diagnostics provide stronger evidence "
            "for a spatially lagged dependent-variable process. "
            "A Spatial Lag specification may be considered in the "
            "next modeling stage."
        )

    elif (
        robust_error_sig
        and robust_lag_sig
    ):

        indication = (
            "Both Robust LM Tests Significant"
        )

        interpretation = (
            "Both robust LM diagnostics are statistically significant. "
            "The source of spatial dependence is therefore not resolved "
            "by these diagnostics alone, and additional specification "
            "assessment is recommended."
        )

    elif (
        lm_error_sig
        or lm_lag_sig
    ):

        indication = (
            "Non-Robust LM Evidence"
        )

        interpretation = (
            "At least one conventional LM diagnostic is significant, "
            "but the corresponding robust diagnostics do not provide "
            "clear support for a single spatial specification."
        )

    elif residual_spatial_dependence:

        indication = (
            "Residual Spatial Dependence"
        )

        interpretation = (
            "Residual Moran's I indicates remaining spatial "
            "autocorrelation, although the selected LM diagnostics "
            "do not clearly identify a spatial lag or spatial error "
            "alternative."
        )

    else:

        indication = (
            "No Strong Spatial Dependence Detected"
        )

        interpretation = (
            "The selected diagnostics do not provide strong evidence "
            "of residual spatial dependence at the selected "
            "significance threshold."
        )

    return {
        "residual_spatial_dependence":
            residual_spatial_dependence,

        "model_indication":
            indication,

        "interpretation":
            interpretation,
    }


# ============================================================
# MAIN ANALYSIS
# ============================================================

def calculate_spatial_regression(
    geojson_data: dict,
    geography_column: str,
    dependent_column: str,
    independent_columns: list[str],
    significance_level: float = DEFAULT_SIGNIFICANCE_LEVEL,
) -> dict:
    """
    Run OLS regression and spatial diagnostics.

    Parameters
    ----------
    geojson_data
        Polygon GeoJSON FeatureCollection.

    geography_column
        Unique polygon identifier.

    dependent_column
        Dependent variable Y.

    independent_columns
        One or more explanatory variables X.

    significance_level
        Threshold used only for SENSD interpretation of diagnostic
        p-values. Default = 0.05.

    Returns
    -------
    dict
        {
            "summary": {...},
            "coefficients": [...],
            "records": [...]
        }
    """

    # --------------------------------------------------------
    # Validate significance threshold
    # --------------------------------------------------------

    try:
        significance_level = float(
            significance_level
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise ValueError(
            "Significance level must be numeric."
        ) from exc

    if not (
        0
        < significance_level
        <= 1
    ):
        raise ValueError(
            "Significance level must be greater than 0 and "
            "less than or equal to 1."
        )

    # --------------------------------------------------------
    # Prepare data
    # --------------------------------------------------------

    gdf = (
        prepare_spatial_regression_geodataframe(
            geojson_data=
                geojson_data,

            geography_column=
                geography_column,

            dependent_column=
                dependent_column,

            independent_columns=
                independent_columns,
        )
    )

    independent_columns = [
        str(column).strip()
        for column in independent_columns
    ]

    observation_count = len(
        gdf
    )

    # --------------------------------------------------------
    # Spatial weights
    # --------------------------------------------------------

    (
        weights_graph,
        weights,
    ) = _build_spatial_weights(
        gdf
    )

    neighbor_counts = (
        _get_neighbor_counts(
            weights_graph,
            observation_count,
        )
    )

    island_count = int(
        (
            neighbor_counts
            <= 0
        ).sum()
    )

    # --------------------------------------------------------
    # Regression arrays
    # --------------------------------------------------------

    y = (
        gdf[
            dependent_column
        ]
        .to_numpy(
            dtype=float
        )
        .reshape(
            -1,
            1
        )
    )

    x = (
        gdf[
            independent_columns
        ]
        .to_numpy(
            dtype=float
        )
    )

    # --------------------------------------------------------
    # Check design matrix rank
    # --------------------------------------------------------
    #
    # spreg.OLS will add the intercept internally.
    # We check predictor rank here to catch exact collinearity
    # before fitting.
    # --------------------------------------------------------

    # Check predictors together with the intercept added by OLS.
    design_matrix = np.column_stack(
        [np.ones(observation_count), x]
    )

    if np.linalg.matrix_rank(design_matrix) < design_matrix.shape[1]:
        raise ValueError(
            "The selected independent variables are perfectly "
            "collinear when the intercept is included. "
            "Remove one or more redundant variables."
        )                                                               

    # --------------------------------------------------------
    # OLS
    # --------------------------------------------------------

    try:
        ols_model = (
            spreg.OLS(
                y,
                x,
                name_y=
                    dependent_column,
                name_x=
                    independent_columns,
                name_ds=
                    "SENSD Spatial Regression",
            )
        )

    except Exception as exc:
        raise ValueError(
            "OLS regression could not be estimated. "
            "Check the selected variables for collinearity, "
            "insufficient variation, or numerical problems."
        ) from exc

    # --------------------------------------------------------
    # Spatial diagnostics
    # --------------------------------------------------------

    # Preserve OLS results even when spatial diagnostics are unavailable.
    lm_tests = None
    residual_moran = None
    diagnostic_errors = []

    if not np.any(neighbor_counts > 0):
        diagnostic_errors.append(
            "No Queen-contiguity neighbors were found. "
            "OLS results are available, but spatial diagnostics "
            "cannot be calculated."
        )
    else:
        try:
            lm_tests = spreg.LMtests(
                ols_model,
                weights,
                tests=["lme", "rlme", "lml", "rlml"],
            )
        except Exception:
            diagnostic_errors.append(
                "Spatial LM diagnostics could not be calculated."
            )

        try:
            residual_moran = spreg.MoranRes(
                ols_model,
                weights,
                z=True,
            )
        except Exception:
            diagnostic_errors.append(
                "Residual Moran's I could not be calculated."
            )
            
    # --------------------------------------------------------
    # Extract LM diagnostics
    # --------------------------------------------------------

    lm_error = (
        _test_result(
            getattr(
                lm_tests,
                "lme",
                None,
            ),
            significance_level,
        )
    )

    robust_lm_error = (
        _test_result(
            getattr(
                lm_tests,
                "rlme",
                None,
            ),
            significance_level,
        )
    )

    lm_lag = (
        _test_result(
            getattr(
                lm_tests,
                "lml",
                None,
            ),
            significance_level,
        )
    )

    robust_lm_lag = (
        _test_result(
            getattr(
                lm_tests,
                "rlml",
                None,
            ),
            significance_level,
        )
    )

    # --------------------------------------------------------
    # Residual Moran's I
    # --------------------------------------------------------

    residual_moran_i = (
        _json_safe(
            getattr(
                residual_moran,
                "I",
                None,
            )
        )
    )

    residual_moran_expected = (
        _json_safe(
            getattr(
                residual_moran,
                "eI",
                None,
            )
        )
    )

    residual_moran_variance = (
        _json_safe(
            getattr(
                residual_moran,
                "vI",
                None,
            )
        )
    )

    residual_moran_z = (
        _json_safe(
            getattr(
                residual_moran,
                "zI",
                None,
            )
        )
    )

    residual_moran_p = (
        _json_safe(
            getattr(
                residual_moran,
                "p_norm",
                None,
            )
        )
    )

    # --------------------------------------------------------
    # Model diagnostic interpretation
    # --------------------------------------------------------

    diagnostic_interpretation = (
        _diagnostic_interpretation(
            residual_moran_p=
                residual_moran_p,

            lm_error=
                lm_error,

            robust_lm_error=
                robust_lm_error,

            lm_lag=
                lm_lag,

            robust_lm_lag=
                robust_lm_lag,

            significance_level=
                significance_level,
        )
    )

    # --------------------------------------------------------
    # Coefficients
    # --------------------------------------------------------

    betas = np.asarray(
        ols_model.betas
    ).flatten()

    standard_errors = np.asarray(
        ols_model.std_err
    ).flatten()

    t_statistics = list(
        getattr(
            ols_model,
            "t_stat",
            [],
        )
    )

    coefficient_names = [
        "CONSTANT",
        *independent_columns,
    ]

    coefficients = []

    for index, name in enumerate(
        coefficient_names
    ):

        coefficient = (
            _json_safe(
                betas[index]
            )
            if index < len(
                betas
            )
            else None
        )

        standard_error = (
            _json_safe(
                standard_errors[
                    index
                ]
            )
            if index < len(
                standard_errors
            )
            else None
        )

        if index < len(
            t_statistics
        ):

            t_statistic = (
                _json_safe(
                    t_statistics[
                        index
                    ][0]
                )
            )

            p_value = (
                _json_safe(
                    t_statistics[
                        index
                    ][1]
                )
            )

        else:

            t_statistic = None
            p_value = None

        coefficients.append(
            {
                "variable":
                    (
                        "Intercept"
                        if name ==
                        "CONSTANT"
                        else name
                    ),

                "coefficient":
                    coefficient,

                "standard_error":
                    standard_error,

                "t_statistic":
                    t_statistic,

                "p_value":
                    p_value,

                "significant":
                    bool(
                        p_value is not None
                        and float(
                            p_value
                        )
                        <= significance_level
                    ),
            }
        )

    # --------------------------------------------------------
    # Predictions / residuals
    # --------------------------------------------------------

    predicted_values = (
        np.asarray(
            ols_model.predy
        )
        .flatten()
    )

    residual_values = (
        np.asarray(
            ols_model.u
        )
        .flatten()
    )

    # --------------------------------------------------------
    # Standardized residuals
    # --------------------------------------------------------

    residual_std = float(
        np.std(
            residual_values,
            ddof=1,
        )
    )

    if (
        math.isfinite(
            residual_std
        )
        and residual_std > 0
    ):

        standardized_residuals = (
            residual_values
            / residual_std
        )

    else:

        standardized_residuals = (
            np.zeros_like(
                residual_values,
                dtype=float,
            )
        )

    # --------------------------------------------------------
    # Per-geography output
    # --------------------------------------------------------

    records = []

    for index in range(
        observation_count
    ):

        geography = (
            _clean_geography_value(
                gdf.iloc[
                    index
                ][
                    geography_column
                ]
            )
        )

        independent_values = {
            column:
                _json_safe(
                    gdf.iloc[
                        index
                    ][
                        column
                    ]
                )

            for column
            in independent_columns
        }

        records.append(
            {
                "geography":
                    geography,

                "observed_value":
                    _json_safe(
                        y[
                            index,
                            0
                        ]
                    ),

                "predicted_value":
                    _json_safe(
                        predicted_values[
                            index
                        ]
                    ),

                "residual":
                    _json_safe(
                        residual_values[
                            index
                        ]
                    ),

                "standardized_residual":
                    _json_safe(
                        standardized_residuals[
                            index
                        ]
                    ),

                "neighbor_count":
                    int(
                        neighbor_counts[
                            index
                        ]
                    ),

                "is_island":
                    bool(
                        neighbor_counts[
                            index
                        ]
                        <= 0
                    ),

                "independent_values":
                    independent_values,
            }
        )

    # --------------------------------------------------------
    # Model fit statistics
    # --------------------------------------------------------

    r_squared = (
        _json_safe(
            getattr(
                ols_model,
                "r2",
                None,
            )
        )
    )

    adjusted_r_squared = (
        _json_safe(
            getattr(
                ols_model,
                "ar2",
                None,
            )
        )
    )

    log_likelihood = (
        _json_safe(
            getattr(
                ols_model,
                "logll",
                None,
            )
        )
    )

    akaike_information_criterion = (
        _json_safe(
            getattr(
                ols_model,
                "aic",
                None,
            )
        )
    )

    schwarz_criterion = (
        _json_safe(
            getattr(
                ols_model,
                "schwarz",
                None,
            )
        )
    )

    residual_sum_squares = (
        _json_safe(
            getattr(
                ols_model,
                "utu",
                None,
            )
        )
    )

    sigma_squared = (
        _json_safe(
            getattr(
                ols_model,
                "sig2",
                None,
            )
        )
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    summary = {

        "analysis_name":
            "Spatial Regression Analysis",

        "method":
            "OLS Regression with Spatial Diagnostics",

        "software":
            "PySAL spreg",

        "dependent_variable":
            dependent_column,

        "independent_variables":
            independent_columns,

        "observations":
            observation_count,

        "predictor_count":
            len(
                independent_columns
            ),

        "significance_level":
            significance_level,

        # ----------------------------------------------------
        # Spatial weights
        # ----------------------------------------------------

        "spatial_weights":
            "Queen contiguity",

        "rook":
            False,

        "weight_transformation":
            "Row-standardized",

        "island_count":
            island_count,

        "mean_neighbors":
            _json_safe(
                neighbor_counts.mean()
            ),

        "minimum_neighbors":
            _json_safe(
                neighbor_counts.min()
            ),

        "maximum_neighbors":
            _json_safe(
                neighbor_counts.max()
            ),

        # ----------------------------------------------------
        # Model fit
        # ----------------------------------------------------

        "r_squared":
            r_squared,

        "adjusted_r_squared":
            adjusted_r_squared,

        "log_likelihood":
            log_likelihood,

        "aic":
            akaike_information_criterion,

        "schwarz_bic":
            schwarz_criterion,

        "residual_sum_squares":
            residual_sum_squares,

        "sigma_squared":
            sigma_squared,

        # ----------------------------------------------------
        # Residual Moran's I
        # ----------------------------------------------------

        "residual_moran_i":
            residual_moran_i,

        "residual_moran_expected":
            residual_moran_expected,

        "residual_moran_variance":
            residual_moran_variance,

        "residual_moran_z_score":
            residual_moran_z,

        "residual_moran_p_value":
            residual_moran_p,

        "residual_moran_significant": (
            None
            if residual_moran_p is None
            else bool(residual_moran_p <= significance_level)
        ),

        # ----------------------------------------------------
        # LM diagnostics
        # ----------------------------------------------------

        "lm_error":
            lm_error,

        "robust_lm_error":
            robust_lm_error,

        "lm_lag":
            lm_lag,

        "robust_lm_lag":
            robust_lm_lag,

        "diagnostic_errors": 
            diagnostic_errors,

        # ----------------------------------------------------
        # Interpretation
        # ----------------------------------------------------

        "residual_spatial_dependence":
            diagnostic_interpretation[
                "residual_spatial_dependence"
            ],

        "model_indication":
            diagnostic_interpretation[
                "model_indication"
            ],

        "diagnostic_interpretation":
            diagnostic_interpretation[
                "interpretation"
            ],

        "interpretation_note":
            (
                "Spatial diagnostics provide evidence about model "
                "specification but do not independently establish "
                "causality or prove that a single spatial model is "
                "the uniquely correct specification."
            ),
    }

    return {
        "summary":
            summary,

        "coefficients":
            coefficients,

        "records":
            records,
    }
