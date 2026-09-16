"""
SENSD Spatial Association Analysis
==================================

Method
------
Global Bivariate Moran's I
Local Bivariate Moran's I / Bivariate LISA

Purpose
-------
This module evaluates whether values of variable X at a geographic
location are spatially associated with values of variable Y in
neighboring geographic locations.

Conceptually:

    X_i  <-->  spatial lag of Y_j

This is different from a conventional Pearson correlation.

Pearson correlation compares X_i with Y_i within the same geographic
unit.

Bivariate Moran's I compares X_i with spatially weighted values of Y
in neighboring geographic units.

Spatial weights
---------------
SENSD uses:

    Queen contiguity
    rook=False

and:

    row-standardized weights
    transform("r")

This is kept consistent with the SENSD Local Moran's I hotspot-analysis
tool.

Statistical inference
---------------------
Permutation inference is used.

Default settings:

    permutations = 999
    significance level = 0.05
    random seed = 12345

The 999-permutation default is consistent with PySAL/esda.

The significance threshold of 0.05 is an SENSD application default.

The seed of 12345 is used for reproducibility.

Software implementation
-----------------------
This module uses the public PySAL/esda API:

    esda.Moran_BV
    esda.Moran_Local_BV
    libpysal.graph.Graph

It does NOT copy or reproduce PySAL's internal implementation.

Published methodological reference
----------------------------------
Wartenberg, D. (1985).
Multivariate Spatial Correlation: A Method for Exploratory
Geographical Analysis.
Geographical Analysis, 17(4), 263-283.
https://doi.org/10.1111/j.1538-4632.1985.tb00849.x

Related methodological literature
----------------------------------
Lee, S.-I. (2001).
Developing a bivariate spatial association measure:
An integration of Pearson's r and Moran's I.
Journal of Geographical Systems, 3, 369-385.
https://doi.org/10.1007/s101090100064

PySAL/esda software
-------------------
PySAL Exploratory Spatial Data Analysis (esda)

Official implementation:
https://github.com/pysal/esda

Official documentation:
https://pysal.org/esda/

Important interpretation
------------------------
Bivariate Moran's I is directional.

    Moran_BV(X, Y)

is not necessarily equal to:

    Moran_BV(Y, X)

because the statistic relates X at the focal location to the spatial
lag of Y in neighboring locations.

SENSD therefore explicitly labels the analysis direction as:

    X -> spatial lag of Y
"""

from __future__ import annotations

import math
import threading
from typing import Any

import esda
import geopandas as gpd
import numpy as np
import pandas as pd
from libpysal import graph


# ============================================================
# DEFAULT SETTINGS
# ============================================================

DEFAULT_PERMUTATIONS = 999
DEFAULT_SIGNIFICANCE_LEVEL = 0.05
DEFAULT_RANDOM_SEED = 12345


# ============================================================
# GLOBAL MORAN RNG LOCK
# ============================================================
#
# esda.Moran_Local_BV accepts a seed directly.
#
# esda.Moran_BV currently uses NumPy's global random permutation
# generator rather than exposing a seed argument.
#
# To make SENSD results reproducible without leaving NumPy's
# global RNG changed after analysis, we temporarily save the RNG
# state, set the requested seed, calculate Moran_BV, and restore
# the previous state.
#
# A lock prevents two Django threads within the same process from
# changing that global RNG state simultaneously.
# ============================================================

_GLOBAL_MORAN_RNG_LOCK = threading.Lock()


# ============================================================
# QUADRANT CLASSIFICATION
# ============================================================
#
# PySAL default scheme when geoda_quads=False:
#
#     1 = HH
#     2 = LH
#     3 = LL
#     4 = HL
#
# Here the interpretation is:
#
#     focal X value
#          versus
#     spatial lag of neighboring Y values
#
# ============================================================

BIVARIATE_QUADRANT_CLASSIFICATION = {

    1: {
        "cluster_code": "HH",
        "cluster_label": "High X - High Neighboring Y",
        "interpretation": "Positive Spatial Association",
        "description": (
            "A relatively high X value occurs in a location whose "
            "neighbors have relatively high Y values."
        ),
    },

    2: {
        "cluster_code": "LH",
        "cluster_label": "Low X - High Neighboring Y",
        "interpretation": "Negative Spatial Association",
        "description": (
            "A relatively low X value occurs in a location whose "
            "neighbors have relatively high Y values."
        ),
    },

    3: {
        "cluster_code": "LL",
        "cluster_label": "Low X - Low Neighboring Y",
        "interpretation": "Positive Spatial Association",
        "description": (
            "A relatively low X value occurs in a location whose "
            "neighbors have relatively low Y values."
        ),
    },

    4: {
        "cluster_code": "HL",
        "cluster_label": "High X - Low Neighboring Y",
        "interpretation": "Negative Spatial Association",
        "description": (
            "A relatively high X value occurs in a location whose "
            "neighbors have relatively low Y values."
        ),
    },
}

# ============================================================
# JSON-SAFE HELPER
# ============================================================

def _json_safe(value: Any) -> Any:
    """
    Convert NumPy/Pandas values into JSON-safe Python values.
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

    if pd.isna(value):
        return None

    return value


# ============================================================
# GEOGRAPHY CLEANING
# ============================================================

def _clean_geography_value(value: Any) -> str:
    """
    Convert a geography identifier into a clean string.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


# ============================================================
# NUMERIC SETTING VALIDATION
# ============================================================

def _validate_settings(
    permutations: int,
    significance_level: float,
    seed: int,
) -> tuple[int, float, int]:
    """
    Validate statistical settings.
    """

    try:
        permutations = int(permutations)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Permutations must be an integer."
        ) from exc

    if permutations < 1:
        raise ValueError(
            "Permutations must be at least 1."
        )

    try:
        significance_level = float(
            significance_level
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Significance level must be numeric."
        ) from exc

    if not (
        0 < significance_level <= 1
    ):
        raise ValueError(
            "Significance level must be greater than 0 and "
            "less than or equal to 1."
        )

    try:
        seed = int(seed)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Random seed must be an integer."
        ) from exc

    return (
        permutations,
        significance_level,
        seed,
    )


# ============================================================
# PREPARE GEODATAFRAME
# ============================================================

def prepare_spatial_association_geodataframe(
    geojson_data: dict,
    geography_column: str,
    x_column: str,
    y_column: str,
) -> gpd.GeoDataFrame:
    """
    Validate and prepare polygon data for Bivariate Moran analysis.

    Requirements
    ------------
    - GeoJSON FeatureCollection
    - Polygon or MultiPolygon geometry
    - unique geography identifier
    - numeric X variable
    - numeric Y variable
    - at least 3 valid geographic observations
    - variation in both X and Y
    """

    if not isinstance(
        geojson_data,
        dict,
    ):
        raise ValueError(
            "GeoJSON data must be a valid object."
        )

    if (
        geojson_data.get("type")
        != "FeatureCollection"
    ):
        raise ValueError(
            "Spatial Association Analysis requires a "
            "GeoJSON FeatureCollection."
        )

    features = (
        geojson_data.get("features")
        or []
    )

    if not features:
        raise ValueError(
            "The GeoJSON dataset contains no features."
        )

    try:
        gdf = (
            gpd.GeoDataFrame
            .from_features(
                features
            )
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
        x_column,
        y_column,
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in gdf.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required fields: "
            + ", ".join(
                missing_columns
            )
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
    # Polygon requirement
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
            "Spatial Association Analysis currently requires "
            "Polygon or MultiPolygon geometry. Unsupported "
            "geometry types found: "
            + ", ".join(
                sorted(
                    unsupported_types
                )
            )
        )

    # --------------------------------------------------------
    # Repair invalid polygon geometry where possible
    # --------------------------------------------------------

    invalid_mask = (
        ~gdf.geometry.is_valid
    )

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
            # If make_valid is unavailable or fails,
            # invalid geometries are removed below.
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

    duplicated_geographies = (
        gdf[
            geography_column
        ]
        .duplicated(
            keep=False
        )
    )

    if (
        duplicated_geographies.any()
    ):

        duplicate_examples = (
            gdf.loc[
                duplicated_geographies,
                geography_column,
            ]
            .astype(str)
            .drop_duplicates()
            .head(5)
            .tolist()
        )

        raise ValueError(
            "Geography Field must uniquely identify each polygon. "
            "Duplicate values were found"
            + (
                ": "
                + ", ".join(
                    duplicate_examples
                )
                if duplicate_examples
                else "."
            )
        )

    # --------------------------------------------------------
    # Numeric X and Y
    # --------------------------------------------------------

    gdf[x_column] = (
        pd.to_numeric(
            gdf[x_column],
            errors="coerce",
        )
    )

    gdf[y_column] = (
        pd.to_numeric(
            gdf[y_column],
            errors="coerce",
        )
    )

    finite_mask = (
        np.isfinite(
            gdf[
                x_column
            ]
        )
        &
        np.isfinite(
            gdf[
                y_column
            ]
        )
    )

    gdf = gdf[
        finite_mask
    ].copy()

    if len(gdf) < 3:
        raise ValueError(
            "Spatial Association Analysis requires at least "
            "3 polygons with valid numeric values for both "
            "selected variables."
        )

    if (
        gdf[
            x_column
        ]
        .nunique(
            dropna=True
        )
        < 2
    ):
        raise ValueError(
            f"Variable X ({x_column}) must contain at least "
            "two distinct numeric values."
        )

    if (
        gdf[
            y_column
        ]
        .nunique(
            dropna=True
        )
        < 2
    ):
        raise ValueError(
            f"Variable Y ({y_column}) must contain at least "
            "two distinct numeric values."
        )

    # Stable row order is important because spatial weights and
    # PySAL result arrays must remain aligned.
    gdf = gdf.reset_index(
        drop=True
    )

    return gdf


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
# GLOBAL BIVARIATE MORAN
# ============================================================

def _calculate_global_bivariate_moran(
    x_values: np.ndarray,
    y_values: np.ndarray,
    weights_graph,
    permutations: int,
    seed: int,
):
    """
    Calculate global Bivariate Moran's I using esda.Moran_BV.

    Moran_BV currently does not expose a seed argument.
    NumPy RNG state is therefore temporarily controlled and restored.
    """

    with _GLOBAL_MORAN_RNG_LOCK:

        previous_state = (
            np.random.get_state()
        )

        try:
            np.random.seed(
                seed
            )

            result = (
                esda.Moran_BV(
                    x_values,
                    y_values,
                    weights_graph,
                    transformation="r",
                    permutations=permutations,
                )
            )

        finally:
            np.random.set_state(
                previous_state
            )

    return result


# ============================================================
# GLOBAL INTERPRETATION
# ============================================================

def _interpret_global_association(
    moran_i: float,
    p_value: float | None,
    significance_level: float,
) -> dict:
    """
    Produce a human-readable interpretation of the global statistic.
    """

    if (
        p_value is None
        or not math.isfinite(
            float(
                p_value
            )
        )
    ):
        return {
            "direction": "Undetermined",
            "significant": False,
            "interpretation": (
                "Statistical significance could not be determined."
            ),
        }

    significant = (
        float(p_value)
        <= significance_level
    )

    if moran_i > 0:

        direction = (
            "Positive"
        )

        if significant:
            interpretation = (
                "Statistically significant positive spatial association: "
                "higher X values tend to be associated with higher "
                "neighboring Y values, while lower X values tend to be "
                "associated with lower neighboring Y values."
            )

        else:
            interpretation = (
                "Positive spatial association was observed, but it was "
                "not statistically significant at the selected threshold."
            )

    elif moran_i < 0:

        direction = (
            "Negative"
        )

        if significant:
            interpretation = (
                "Statistically significant negative spatial association: "
                "higher X values tend to be associated with lower "
                "neighboring Y values, and vice versa."
            )

        else:
            interpretation = (
                "Negative spatial association was observed, but it was "
                "not statistically significant at the selected threshold."
            )

    else:

        direction = (
            "None"
        )

        interpretation = (
            "The global Bivariate Moran's I is approximately zero, "
            "indicating little evidence of spatial cross-association "
            "between X and neighboring Y values."
        )

    return {
        "direction": direction,
        "significant": significant,
        "interpretation": interpretation,
    }


# ============================================================
# LOCAL CLASSIFICATION
# ============================================================

def classify_local_bivariate_result(
    quadrant: int,
    p_value: float | None,
    neighbor_count: int,
    significance_level: float,
) -> dict:
    """
    Convert a local Bivariate Moran result into a SENSD category.
    """

    if neighbor_count <= 0:
        return {
            "cluster_code": "ISLAND",
            "cluster_label": "No Neighbors",
            "interpretation": "Isolated Polygon",
            "description": (
                "This polygon has no Queen-contiguity neighbors, "
                "so a local spatial association cannot be interpreted."
            ),
            "significant": False,
        }

    if (
        p_value is None
        or not math.isfinite(
            float(
                p_value
            )
        )
    ):
        return {
            "cluster_code": "NS",
            "cluster_label": "Not Significant",
            "interpretation": "Not Significant",
            "description": (
                "A valid local permutation p-value was not available."
            ),
            "significant": False,
        }

    if (
        float(p_value)
        > significance_level
    ):
        return {
            "cluster_code": "NS",
            "cluster_label": "Not Significant",
            "interpretation": "Not Significant",
            "description": (
                "The local spatial association is not statistically "
                "significant at the selected significance level."
            ),
            "significant": False,
        }

    classification = (
        BIVARIATE_QUADRANT_CLASSIFICATION
        .get(
            int(
                quadrant
            )
        )
    )

    if classification is None:
        return {
            "cluster_code": "NS",
            "cluster_label": "Not Significant",
            "interpretation": "Unknown Quadrant",
            "description": (
                "The local spatial association quadrant could "
                "not be classified."
            ),
            "significant": False,
        }

    return {
        **classification,
        "significant": True,
    }


# ============================================================
# MAIN ANALYSIS
# ============================================================

def calculate_spatial_association(
    geojson_data: dict,
    geography_column: str,
    x_column: str,
    y_column: str,
    permutations: int = DEFAULT_PERMUTATIONS,
    significance_level: float = DEFAULT_SIGNIFICANCE_LEVEL,
    seed: int = DEFAULT_RANDOM_SEED,
) -> dict:
    """
    Calculate Global and Local Bivariate Moran's I.

    Parameters
    ----------
    geojson_data
        GeoJSON FeatureCollection containing polygon features.

    geography_column
        Unique polygon identifier.

    x_column
        Focal variable X.

    y_column
        Neighboring variable Y.

    permutations
        Number of random permutations.

    significance_level
        SENSD significance threshold for local/global interpretation.

    seed
        Random seed for reproducibility.

    Returns
    -------
    dict
        {
            "summary": {...},
            "records": [...]
        }

    Direction
    ---------
    The analysis is directional:

        X -> spatial lag of Y

    Swapping X and Y can produce a different Bivariate Moran statistic.
    """

    (
        permutations,
        significance_level,
        seed,
    ) = _validate_settings(
        permutations,
        significance_level,
        seed,
    )

    gdf = (
        prepare_spatial_association_geodataframe(
            geojson_data=geojson_data,
            geography_column=geography_column,
            x_column=x_column,
            y_column=y_column,
        )
    )

    # --------------------------------------------------------
    # Spatial weights
    # --------------------------------------------------------
    #
    # rook=False means Queen contiguity:
    #
    # polygons are neighbors when they share an edge or vertex.
    #
    # --------------------------------------------------------

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

    observation_count = (
        len(
            gdf
        )
    )

    neighbor_counts = _get_neighbor_counts(
    weights_graph,
    observation_count,
    )

    if not np.any(neighbor_counts > 0):
        raise ValueError(
            "No Queen-contiguity neighbors were found. "
            "Spatial association requires analyzed polygons "
            "that share boundary points or edges."
        )

    island_mask = (
        neighbor_counts
        <= 0
    )

    island_count = int(
        island_mask.sum()
    )

    # --------------------------------------------------------
    # Analysis arrays
    # --------------------------------------------------------

    x_values = (
        gdf[
            x_column
        ]
        .to_numpy(
            dtype=float
        )
    )

    y_values = (
        gdf[
            y_column
        ]
        .to_numpy(
            dtype=float
        )
    )

    # --------------------------------------------------------
    # Same-location Pearson correlation
    # --------------------------------------------------------
    #
    # This is included only as contextual information.
    #
    # It is NOT the spatial association statistic.
    #
    # --------------------------------------------------------

    pearson_correlation = float(
        np.corrcoef(
            x_values,
            y_values,
        )[0, 1]
    )

    # --------------------------------------------------------
    # Global Bivariate Moran's I
    # --------------------------------------------------------

    global_moran = (
        _calculate_global_bivariate_moran(
            x_values=x_values,
            y_values=y_values,
            weights_graph=weights_graph,
            permutations=permutations,
            seed=seed,
        )
    )

    global_i = float(
        global_moran.I
    )

    global_p = _json_safe(
        getattr(
            global_moran,
            "p_sim",
            None,
        )
    )

    global_z = _json_safe(
        getattr(
            global_moran,
            "z_sim",
            None,
        )
    )

    global_expected = _json_safe(
        getattr(
            global_moran,
            "EI_sim",
            None,
        )
    )

    global_interpretation = (
        _interpret_global_association(
            moran_i=global_i,
            p_value=global_p,
            significance_level=significance_level,
        )
    )

    # --------------------------------------------------------
    # Local Bivariate Moran's I
    # --------------------------------------------------------

    local_moran = (
        esda.Moran_Local_BV(
            x_values,
            y_values,
            weights_graph,
            transformation="r",
            permutations=permutations,
            geoda_quads=False,
            n_jobs=1,
            keep_simulations=False,
            seed=seed,
            island_weight=0,
        )
    )

    local_i_values = (
        np.asarray(
            local_moran.Is
        )
    )

    local_p_values = (
        np.asarray(
            local_moran.p_sim
        )
    )

    local_quadrants = (
        np.asarray(
            local_moran.q
        )
    )

    standardized_x = (
        np.asarray(
            local_moran.zx
        )
    )

    standardized_y = (
        np.asarray(
            local_moran.zy
        )
    )

    # --------------------------------------------------------
    # Spatial lag of standardized Y
    # --------------------------------------------------------

    try:
        spatial_lag_y = (
            np.asarray(
                weights_graph.lag(
                    standardized_y
                )
            )
        )

    except Exception:
        spatial_lag_y = (
            np.full(
                observation_count,
                np.nan,
            )
        )

    # --------------------------------------------------------
    # Build records
    # --------------------------------------------------------

    records = []

    cluster_counts = {
        "HH": 0,
        "LL": 0,
        "HL": 0,
        "LH": 0,
        "NS": 0,
        "ISLAND": 0,
    }

    significant_count = 0

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

        x_value = (
            float(
                x_values[
                    index
                ]
            )
        )

        y_value = (
            float(
                y_values[
                    index
                ]
            )
        )

        local_i = (
            _json_safe(
                local_i_values[
                    index
                ]
            )
        )

        pseudo_p_value = (
            _json_safe(
                local_p_values[
                    index
                ]
            )
        )

        quadrant = int(
            local_quadrants[
                index
            ]
        )

        neighbor_count = int(
            neighbor_counts[
                index
            ]
        )

        # Spatial test results are not interpretable without neighbors.
        if neighbor_count == 0:
            local_i = None
            pseudo_p_value = None
            quadrant = None

        classification = (
            classify_local_bivariate_result(
                quadrant=quadrant,
                p_value=pseudo_p_value,
                neighbor_count=neighbor_count,
                significance_level=significance_level,
            )
        )

        cluster_code = (
            classification[
                "cluster_code"
            ]
        )

        if (
            cluster_code
            in cluster_counts
        ):
            cluster_counts[
                cluster_code
            ] += 1

        if classification[
            "significant"
        ]:
            significant_count += 1

        record = {

            "geography": geography,

            "x_value": x_value,

            "y_value": y_value,

            "standardized_x": (
                _json_safe(
                    standardized_x[
                        index
                    ]
                )
            ),

            "standardized_y": (
                _json_safe(
                    standardized_y[
                        index
                    ]
                )
            ),

            "spatial_lag_y": (
                None
                if neighbor_count == 0
                else _json_safe(spatial_lag_y[index])
            ),

            "local_bivariate_moran_i": (
                local_i
            ),

            "pseudo_p_value": (
                pseudo_p_value
            ),

            # Alias retained for frontend convenience.
            "p_value": (
                pseudo_p_value
            ),

            "quadrant": (
                quadrant
            ),

            "cluster_code": (
                cluster_code
            ),

            "cluster_label": (
                classification[
                    "cluster_label"
                ]
            ),

            "interpretation": (
                classification[
                    "interpretation"
                ]
            ),

            "description": (
                classification[
                    "description"
                ]
            ),

            "significant": (
                classification[
                    "significant"
                ]
            ),

            "neighbor_count": (
                neighbor_count
            ),

            "is_island": (
                neighbor_count
                <= 0
            ),
        }

        records.append(
            record
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    not_significant_count = (
        cluster_counts[
            "NS"
        ]
    )

    summary = {

        "analysis_name": (
            "Spatial Association Analysis"
        ),

        "method": (
            "Bivariate Moran's I"
        ),

        "global_method": (
            "Global Bivariate Moran's I"
        ),

        "local_method": (
            "Local Bivariate Moran's I"
        ),

        "software": (
            "PySAL esda"
        ),

        "analysis_direction": (
            f"{x_column} -> spatial lag of {y_column}"
        ),

        "direction_note": (
            "Bivariate Moran's I is directional. "
            "Swapping Variable X and Variable Y may produce "
            "a different result."
        ),

        "geography_column": (
            geography_column
        ),

        "x_column": (
            x_column
        ),

        "y_column": (
            y_column
        ),

        "observations": (
            observation_count
        ),

        "spatial_weights": (
            "Queen contiguity"
        ),

        "rook": False,

        "weight_transformation": (
            "Row-standardized"
        ),

        "permutations": (
            permutations
        ),

        "significance_level": (
            significance_level
        ),

        "random_seed": (
            seed
        ),

        "multiple_testing_correction": (
            "None"
        ),

        # ----------------------------------------------------
        # Global Bivariate Moran
        # ----------------------------------------------------

        "global_bivariate_moran_i": (
            _json_safe(
                global_i
            )
        ),

        "global_pseudo_p_value": (
            global_p
        ),

        "global_permutation_z_score": (
            global_z
        ),

        "global_expected_i_under_permutations": (
            global_expected
        ),

        "global_direction": (
            global_interpretation[
                "direction"
            ]
        ),

        "global_significant": (
            global_interpretation[
                "significant"
            ]
        ),

        "global_interpretation": (
            global_interpretation[
                "interpretation"
            ]
        ),

        # ----------------------------------------------------
        # Non-spatial comparison
        # ----------------------------------------------------

        "same_location_pearson_correlation": (
            _json_safe(
                pearson_correlation
            )
        ),

        "pearson_note": (
            "Pearson correlation is included only as contextual "
            "information and is not the spatial association statistic."
        ),

        # ----------------------------------------------------
        # Local Bivariate Moran
        # ----------------------------------------------------

        "high_high_count": (
            cluster_counts[
                "HH"
            ]
        ),

        "low_low_count": (
            cluster_counts[
                "LL"
            ]
        ),

        "high_low_count": (
            cluster_counts[
                "HL"
            ]
        ),

        "low_high_count": (
            cluster_counts[
                "LH"
            ]
        ),

        "significant_count": (
            significant_count
        ),

        "not_significant_count": (
            not_significant_count
        ),

        "island_count": (
            island_count
        ),

        "mean_neighbors": (
            _json_safe(
                neighbor_counts.mean()
            )
        ),

        "minimum_neighbors": (
            _json_safe(
                neighbor_counts.min()
            )
        ),

        "maximum_neighbors": (
            _json_safe(
                neighbor_counts.max()
            )
        ),
    }

    return {
        "summary": summary,
        "records": records,
    }
