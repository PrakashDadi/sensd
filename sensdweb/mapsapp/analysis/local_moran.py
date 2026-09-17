# geosens/analysis/local_moran.py

"""
SENSD Hotspot Analysis — Local Moran's I (LISA)

This module performs local spatial autocorrelation analysis using
the public PySAL API.

Reference workflow used for this implementation
------------------------------------------------
The PySAL reference material supplied for this project uses:

    from libpysal import graph
    import esda

    wq = (
        graph.Graph
        .build_contiguity(df, rook=False)
        .transform("r")
    )

    lm = esda.moran.Moran_Local(
        df["median_pri"],
        wq,
        permutations=999,
        seed=12345
    )

Accordingly, SENSD uses:

    - Queen contiguity
    - row-standardized spatial relationships
    - Local Moran's I
    - conditional random permutations
    - 999 permutations
    - random seed 12345

The significance threshold of 0.05 is an SENSD application
default used to classify permutation pseudo p-values. It is not
hard-coded by the PySAL reference workflow itself.

Interpretation
--------------
High-High
    Hot Spot

Low-Low
    Cold Spot

High-Low
    High-value Spatial Outlier

Low-High
    Low-value Spatial Outlier

Not Significant
    No statistically significant local spatial association at
    the selected significance threshold.

Important methodological note
-----------------------------
A separate Local Moran test is conducted for each polygon.
Therefore, the results should be interpreted with awareness of
the multiple comparisons problem.

This initial implementation reports permutation pseudo p-values
without applying an FDR or Bonferroni correction.

Future SENSD versions may provide those correction methods as
optional settings.

This module DOES NOT reproduce the internal PySAL Local Moran
algorithm. It calls the public PySAL API and adds SENSD-specific:

    - input validation
    - geography validation
    - cluster interpretation
    - island handling
    - output formatting

Primary software reference supplied for this project:

@software{esda_2026,
  author       = {Sergio Rey and
                  Levi John Wolf and
                  James Gaboardi and
                  Dani Arribas-Bel and
                  Lee Hachadoorian and
                  Martin Fleischmann and
                  Wei Kang and
                  eli knaap and
                  mhwang4 and
                  Jay Laura and
                  Philip Stephens and
                  Charles Schmidt and
                  Stefanie Lumnitz and
                  David C. Folch and
                  Juan C Duque and
                  Luc Anselin and
                  Nicholas Malizia and
                  Filipe and
                  Thomas Louf and
                  Germano Barcelos and
                  Josiah Parry and
                  Michael Rariden and
                  matthewborish and
                  Jeff Sauer and
                  JasonSteelmanCoder and
                  Leo Morales and
                  mlyons-tcc and
                  Mridul Seth and
                  Nathaniel M. Beaver},
  title        = {pysal/esda: v2.9.0},
  month        = mar,
  year         = 2026,
  publisher    = {Zenodo},
  version      = {v2.9.0},
  doi          = {10.5281/zenodo.19140557},
  url          = {https://doi.org/10.5281/zenodo.19140557}
}

Runtime environment currently used by SENSD:
    esda 2.10.0
    libpysal 4.15.0
"""

import math

import esda
import geopandas as gpd
import numpy as np
import pandas as pd

from libpysal import graph


# ============================================================
# DEFAULT ANALYSIS SETTINGS
# ============================================================

# Directly follows the PySAL reference workflow supplied
# for this project.
DEFAULT_PERMUTATIONS = 999

# Directly follows the PySAL reference workflow supplied
# for this project.
DEFAULT_RANDOM_SEED = 12345

# SENSD application default.
#
# This value is used to determine whether the permutation
# pseudo p-value returned by Moran_Local is considered
# statistically significant.
#
# This threshold is NOT imposed by PySAL.
DEFAULT_SIGNIFICANCE_LEVEL = 0.05


# ============================================================
# PYSAL QUADRANT DEFINITIONS
# ============================================================
#
# PySAL's standard Moran_Local quadrant convention:
#
#     1 = High-High
#     2 = Low-High
#     3 = Low-Low
#     4 = High-Low
#
# We explicitly translate these numeric values into descriptive
# application labels.
# ============================================================

QUADRANT_CLASSIFICATION = {

    1: {
        "cluster_code": "HH",
        "cluster_label": "High-High",
        "interpretation": "Hot Spot",
        "description":
            "A high-value location surrounded by "
            "high-value neighboring locations.",
    },

    2: {
        "cluster_code": "LH",
        "cluster_label": "Low-High",
        "interpretation":
            "Low-value Spatial Outlier",
        "description":
            "A low-value location surrounded by "
            "high-value neighboring locations.",
    },

    3: {
        "cluster_code": "LL",
        "cluster_label": "Low-Low",
        "interpretation": "Cold Spot",
        "description":
            "A low-value location surrounded by "
            "low-value neighboring locations.",
    },

    4: {
        "cluster_code": "HL",
        "cluster_label": "High-Low",
        "interpretation":
            "High-value Spatial Outlier",
        "description":
            "A high-value location surrounded by "
            "low-value neighboring locations.",
    },
}


# ============================================================
# JSON-SAFE VALUE HELPER
# ============================================================

def _json_safe(value):
    """
    Convert NumPy / pandas scalar values into ordinary Python
    values that Django can safely serialize.
    """

    if value is None:
        return None

    if isinstance(
        value,
        np.integer,
    ):
        return int(value)

    if isinstance(
        value,
        np.floating,
    ):

        value = float(value)

        if not math.isfinite(
            value
        ):
            return None

        return value

    if isinstance(
        value,
        np.bool_,
    ):
        return bool(value)

    if isinstance(
        value,
        pd.Timestamp,
    ):
        return value.isoformat()

    if isinstance(
        value,
        float,
    ):

        if not math.isfinite(
            value
        ):
            return None

        return value

    try:

        if pd.isna(
            value
        ):
            return None

    except (
        TypeError,
        ValueError,
    ):
        pass

    if hasattr(
        value,
        "item",
    ):

        try:
            return value.item()

        except Exception:
            pass

    return value


# ============================================================
# TEXT CLEANING
# ============================================================

def _clean_geography_value(
    value,
):
    """
    Convert a geography identifier into a clean string.
    """

    if value is None:
        return ""

    try:

        if pd.isna(
            value
        ):
            return ""

    except (
        TypeError,
        ValueError,
    ):
        pass

    return str(
        value
    ).strip()


# ============================================================
# NUMERIC SETTING VALIDATION
# ============================================================

def _validate_numeric_setting(
    value,
    *,
    name,
    minimum=None,
    maximum=None,
):
    """
    Validate a numeric analysis setting.
    """

    try:

        numeric_value = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        raise ValueError(
            f"{name} must be numeric."
        )

    if not math.isfinite(
        numeric_value
    ):

        raise ValueError(
            f"{name} must be finite."
        )

    if (
        minimum is not None
        and
        numeric_value < minimum
    ):

        raise ValueError(
            f"{name} must be at least {minimum}."
        )

    if (
        maximum is not None
        and
        numeric_value > maximum
    ):

        raise ValueError(
            f"{name} must not exceed {maximum}."
        )

    return numeric_value


# ============================================================
# GEODATAFRAME PREPARATION
# ============================================================

def prepare_local_moran_geodataframe(
    *,
    geojson_data,
    geography_column,
    value_column,
):
    """
    Prepare uploaded polygon GeoJSON for Local Moran's I.

    Requirements:
        - GeoJSON FeatureCollection
        - Polygon or MultiPolygon geometry
        - unique geography identifier
        - numeric analysis variable
        - at least three usable observations
        - variation in the analysis variable

    Missing or non-numeric analysis values are excluded from
    the statistical calculation.
    """

    # --------------------------------------------------------
    # VALIDATE GEOJSON STRUCTURE
    # --------------------------------------------------------

    if not isinstance(
        geojson_data,
        dict,
    ):

        raise ValueError(
            "A valid GeoJSON object is required."
        )

    if (
        geojson_data.get(
            "type"
        )
        !=
        "FeatureCollection"
    ):

        raise ValueError(
            "GeoJSON must be a FeatureCollection."
        )

    features = geojson_data.get(
        "features",
        [],
    )

    if not features:

        raise ValueError(
            "The GeoJSON contains no features."
        )

    # --------------------------------------------------------
    # VALIDATE FIELD SELECTION
    # --------------------------------------------------------

    if not geography_column:

        raise ValueError(
            "Geography field is required."
        )

    if not value_column:

        raise ValueError(
            "Analysis variable is required."
        )

    # --------------------------------------------------------
    # GEOJSON -> GEODATAFRAME
    # --------------------------------------------------------

    try:

        gdf = (
            gpd.GeoDataFrame.from_features(
                features
            )
        )

    except Exception as error:

        raise ValueError(
            "The uploaded GeoJSON could not be converted "
            f"to a GeoDataFrame: {error}"
        )

    if gdf.empty:

        raise ValueError(
            "The GeoJSON contains no usable features."
        )

    # --------------------------------------------------------
    # VALIDATE SELECTED COLUMNS
    # --------------------------------------------------------

    if (
        geography_column
        not in gdf.columns
    ):

        raise ValueError(
            f"Geography field "
            f"'{geography_column}' was not found."
        )

    if (
        value_column
        not in gdf.columns
    ):

        raise ValueError(
            f"Analysis variable "
            f"'{value_column}' was not found."
        )

    if (
        "geometry"
        not in gdf.columns
    ):

        raise ValueError(
            "The dataset does not contain geometry."
        )

    # --------------------------------------------------------
    # REMOVE NULL GEOMETRY
    # --------------------------------------------------------

    gdf = gdf.loc[
        gdf.geometry.notna()
    ].copy()

    if gdf.empty:

        raise ValueError(
            "The dataset contains no valid geometries."
        )

    # --------------------------------------------------------
    # KEEP POLYGON GEOMETRY
    # --------------------------------------------------------

    polygon_mask = (
        gdf.geometry.geom_type.isin(
            [
                "Polygon",
                "MultiPolygon",
            ]
        )
    )

    gdf = gdf.loc[
        polygon_mask
    ].copy()

    if gdf.empty:

        raise ValueError(
            "Hotspot Analysis using Local Moran's I "
            "requires Polygon or MultiPolygon geometry."
        )

    # --------------------------------------------------------
    # REPAIR INVALID GEOMETRY
    # --------------------------------------------------------

    invalid_mask = (
        ~gdf.geometry.is_valid
    )

    if invalid_mask.any():

        try:

            repaired_geometry = (
                gdf.loc[
                    invalid_mask,
                    "geometry",
                ]
                .make_valid()
            )

            gdf.loc[
                invalid_mask,
                "geometry",
            ] = repaired_geometry

        except Exception:

            # If repair fails, remove invalid polygons rather
            # than building unreliable contiguity relationships.
            gdf = gdf.loc[
                gdf.geometry.is_valid
            ].copy()

    if gdf.empty:

        raise ValueError(
            "No valid polygon geometries remain "
            "after geometry validation."
        )
    # Keep only valid, nonempty polygons after geometry repair.
    usable_geometry = (
        gdf.geometry.notna()
        & ~gdf.geometry.is_empty
        & gdf.geometry.is_valid
        & gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    )

    gdf = gdf.loc[usable_geometry].copy()

    if gdf.empty:
        raise ValueError(
            "No valid, nonempty Polygon or MultiPolygon geometries "
            "remain after geometry repair."
        )

    # --------------------------------------------------------
    # CLEAN UNIQUE GEOGRAPHY IDENTIFIER
    # --------------------------------------------------------

    gdf[
        "_sensd_geography"
    ] = (
        gdf[
            geography_column
        ]
        .apply(
            _clean_geography_value
        )
    )

    gdf = gdf.loc[
        gdf[
            "_sensd_geography"
        ]
        !=
        ""
    ].copy()

    if gdf.empty:

        raise ValueError(
            "No valid geography identifiers were found."
        )

    if (
        gdf[
            "_sensd_geography"
        ]
        .duplicated()
        .any()
    ):

        raise ValueError(
            f"The Geography Field '{geography_column}' "
            "contains duplicate values. Choose a unique "
            "polygon identifier such as GEOID."
        )

    # --------------------------------------------------------
    # CONVERT ANALYSIS VARIABLE TO NUMERIC
    # --------------------------------------------------------

    gdf[
        "_sensd_value"
    ] = pd.to_numeric(
        gdf[
            value_column
        ],
        errors="coerce",
    )

    values_array = (
        gdf[
            "_sensd_value"
        ]
        .to_numpy(
            dtype=float
        )
    )

    finite_mask = np.isfinite(
        values_array
    )

    gdf = gdf.loc[
        finite_mask
    ].copy()

    # --------------------------------------------------------
    # MINIMUM OBSERVATIONS
    # --------------------------------------------------------

    if len(
        gdf
    ) < 3:

        raise ValueError(
            "Hotspot Analysis requires at least "
            "three polygons with valid numeric values."
        )

    # --------------------------------------------------------
    # REQUIRE VARIATION
    # --------------------------------------------------------

    if (
        gdf[
            "_sensd_value"
        ]
        .nunique()
        <
        2
    ):

        raise ValueError(
            f"The analysis variable '{value_column}' "
            "does not contain enough variation for "
            "Local Moran's I."
        )

    # --------------------------------------------------------
    # RESET INDEX
    # --------------------------------------------------------

    gdf = gdf.reset_index(
        drop=True
    )

    return gdf


# ============================================================
# GRAPH NEIGHBOR COUNTS
# ============================================================

def _get_neighbor_counts(weights_graph, observation_count):
    """Return neighbor counts aligned with the reset GeoDataFrame index."""
    try:
        cardinalities = weights_graph.cardinalities

        if not isinstance(cardinalities, pd.Series):
            raise ValueError("Unexpected neighbor-count format.")

        expected_index = pd.RangeIndex(observation_count)

        if (
            not cardinalities.index.is_unique
            or len(cardinalities) != observation_count
        ):
            raise ValueError("Neighbor counts do not match the dataset.")

        counts = cardinalities.reindex(expected_index).to_numpy(dtype=float)

        if (
            not np.isfinite(counts).all()
            or (counts < 0).any()
            or (counts != np.floor(counts)).any()
        ):
            raise ValueError("Neighbor counts contain invalid or missing values.")

        return counts.astype(int).tolist()

    except Exception as exc:
        raise ValueError(
            f"Could not retrieve valid spatial neighbor counts: {exc}"
        ) from exc


# ============================================================
# LOCAL MORAN CLASSIFICATION
# ============================================================

def classify_local_moran_result(
    *,
    quadrant,
    p_value,
    significance_level,
    is_island=False,
):
    """
    Translate Local Moran quadrant and permutation pseudo p-value
    into a SENSD map category.
    """

    # --------------------------------------------------------
    # ISOLATED POLYGON
    # --------------------------------------------------------

    if is_island:

        return {

            "cluster_code":
                "ISLAND",

            "cluster_label":
                "No Neighbors",

            "interpretation":
                "Isolated Polygon",

            "significant":
                False,

            "description":
                "This polygon has no Queen-contiguity "
                "neighbors and therefore is not assigned "
                "a Local Moran cluster.",
        }

    # --------------------------------------------------------
    # INVALID / MISSING P-VALUE
    # --------------------------------------------------------

    if p_value is None:

        return {

            "cluster_code":
                "NS",

            "cluster_label":
                "Not Significant",

            "interpretation":
                "Not Significant",

            "significant":
                False,

            "description":
                "No statistically significant local spatial "
                "association was identified.",
        }

    try:

        p_value = float(
            p_value
        )

    except (
        TypeError,
        ValueError,
    ):

        return {

            "cluster_code":
                "NS",

            "cluster_label":
                "Not Significant",

            "interpretation":
                "Not Significant",

            "significant":
                False,

            "description":
                "No statistically significant local spatial "
                "association was identified.",
        }

    if not math.isfinite(
        p_value
    ):

        return {

            "cluster_code":
                "NS",

            "cluster_label":
                "Not Significant",

            "interpretation":
                "Not Significant",

            "significant":
                False,

            "description":
                "No statistically significant local spatial "
                "association was identified.",
        }

    # --------------------------------------------------------
    # SENSD SIGNIFICANCE THRESHOLD
    # --------------------------------------------------------

    if (
        p_value
        >
        significance_level
    ):

        return {

            "cluster_code":
                "NS",

            "cluster_label":
                "Not Significant",

            "interpretation":
                "Not Significant",

            "significant":
                False,

            "description":
                "No statistically significant local spatial "
                "association was identified at the selected "
                "significance threshold.",
        }

    # --------------------------------------------------------
    # SIGNIFICANT QUADRANT
    # --------------------------------------------------------

    quadrant_info = (
        QUADRANT_CLASSIFICATION.get(
            int(
                quadrant
            )
        )
    )

    if not quadrant_info:

        return {

            "cluster_code":
                "NS",

            "cluster_label":
                "Not Significant",

            "interpretation":
                "Not Significant",

            "significant":
                False,

            "description":
                "The observation could not be assigned to "
                "a recognized Local Moran quadrant.",
        }

    return {

        "cluster_code":
            quadrant_info[
                "cluster_code"
            ],

        "cluster_label":
            quadrant_info[
                "cluster_label"
            ],

        "interpretation":
            quadrant_info[
                "interpretation"
            ],

        "significant":
            True,

        "description":
            quadrant_info[
                "description"
            ],
    }


# ============================================================
# MAIN HOTSPOT ANALYSIS
# ============================================================

def calculate_local_moran(
    *,
    geojson_data,
    geography_column,
    value_column,
    permutations=DEFAULT_PERMUTATIONS,
    significance_level=DEFAULT_SIGNIFICANCE_LEVEL,
    seed=DEFAULT_RANDOM_SEED,
):
    """
    Perform SENSD Hotspot Analysis using Local Moran's I.

    Parameters
    ----------
    geojson_data : dict
        Polygon GeoJSON FeatureCollection.

    geography_column : str
        Unique polygon identifier such as GEOID.

    value_column : str
        Numeric variable being analyzed.

    permutations : int
        Number of conditional random permutations.

        SENSD default:
            999

        Source:
            directly follows the supplied PySAL workflow.

    significance_level : float
        Threshold applied by SENSD to the permutation pseudo
        p-value returned by Moran_Local.

        SENSD default:
            0.05

        Important:
            this threshold is an application decision, not a
            PySAL requirement.

    seed : int
        Random seed used by Moran_Local.

        SENSD default:
            12345

        Source:
            directly follows the supplied PySAL workflow.

    Returns
    -------
    dict

        {
            "summary": {...},
            "records": [...]
        }
    """

    # ========================================================
    # VALIDATE PERMUTATIONS
    # ========================================================

    try:

        permutations = int(
            permutations
        )

    except (
        TypeError,
        ValueError,
    ):

        raise ValueError(
            "Permutations must be an integer."
        )

    if permutations < 1:

        raise ValueError(
            "Permutations must be at least 1."
        )

    # ========================================================
    # VALIDATE SIGNIFICANCE LEVEL
    # ========================================================

    significance_level = (
        _validate_numeric_setting(
            significance_level,

            name=
                "Significance level",

            minimum=
                0.000001,

            maximum=
                1.0,
        )
    )

    # ========================================================
    # VALIDATE RANDOM SEED
    # ========================================================

    try:

        seed = int(
            seed
        )

    except (
        TypeError,
        ValueError,
    ):

        raise ValueError(
            "Random seed must be an integer."
        )

    # ========================================================
    # PREPARE GEODATAFRAME
    # ========================================================

    gdf = (
        prepare_local_moran_geodataframe(

            geojson_data=
                geojson_data,

            geography_column=
                geography_column,

            value_column=
                value_column,
        )
    )

    observation_count = len(
        gdf
    )

    # ========================================================
    # QUEEN CONTIGUITY
    # ========================================================
    #
    # This follows the supplied PySAL reference:
    #
    # graph.Graph.build_contiguity(
    #     df,
    #     rook=False
    # ).transform("r")
    #
    # rook=False corresponds to Queen contiguity.
    # ========================================================

    try:

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

    except Exception as error:

        raise ValueError(
            "Queen-contiguity spatial relationships "
            "could not be constructed: "
            f"{error}"
        )

    # ========================================================
    # NEIGHBOR COUNTS / ISLANDS
    # ========================================================

    neighbor_counts = (
        _get_neighbor_counts(
            weights_graph,
            observation_count,
        )
    )

    if not any(count > 0 for count in neighbor_counts):
        raise ValueError(
            "No Queen-contiguity neighbors were found. "
            "The analyzed polygons must share boundary points or edges "
            "for this analysis."
        )

    island_indexes = {
        index
        for index, count
        in enumerate(
            neighbor_counts
        )
        if count == 0
    }

    # ========================================================
    # ANALYSIS VECTOR
    # ========================================================

    values = (
        gdf[
            "_sensd_value"
        ]
        .to_numpy(
            dtype=float
        )
    )

    # ========================================================
    # LOCAL MORAN'S I
    # ========================================================
    #
    # This follows the supplied PySAL workflow:
    #
    # lm = esda.moran.Moran_Local(
    #     df["median_pri"],
    #     wq,
    #     permutations=999,
    #     seed=12345
    # )
    #
    # PySAL provides:
    #
    #     Is
    #         observed Local Moran statistic
    #
    #     p_sim
    #         permutation pseudo p-value
    #
    #     q
    #         Moran scatterplot quadrant
    #
    #     z
    #         standardized observed values
    #
    # ========================================================

    try:

        local_moran = (
            esda.moran.Moran_Local(
                values,
                weights_graph,
                permutations=
                    permutations,
                seed=
                    seed,
            )
        )

    except Exception as error:

        raise ValueError(
            "Local Moran's I calculation failed: "
            f"{error}"
        )

    # ========================================================
    # RESULT COUNTERS
    # ========================================================

    counts = {

        "HH": 0,

        "LL": 0,

        "HL": 0,

        "LH": 0,

        "NS": 0,

        "ISLAND": 0,
    }

    significant_count = 0

    records = []

    # ========================================================
    # BUILD FEATURE-LEVEL RESULTS
    # ========================================================

    for index in range(
        observation_count
    ):

        row = gdf.iloc[
            index
        ]

        geography = (
            row[
                "_sensd_geography"
            ]
        )

        observed_value = (
            row[
                "_sensd_value"
            ]
        )

        local_i = (
            _json_safe(
                local_moran.Is[
                    index
                ]
            )
        )

        pseudo_p_value = (
            _json_safe(
                local_moran.p_sim[
                    index
                ]
            )
        )

        quadrant = int(
            local_moran.q[
                index
            ]
        )

        standardized_value = (
            _json_safe(
                local_moran.z[
                    index
                ]
            )
        )

        neighbor_count = int(
            neighbor_counts[
                index
            ]
        )

        is_island = (
            index
            in
            island_indexes
        )

        # Spatial test results are not interpretable without neighbors.
        if is_island:
            local_i = None
            pseudo_p_value = None
            quadrant = None

        classification = (
            classify_local_moran_result(

                quadrant=
                    quadrant,

                p_value=
                    pseudo_p_value,

                significance_level=
                    significance_level,

                is_island=
                    is_island,
            )
        )

        cluster_code = (
            classification[
                "cluster_code"
            ]
        )

        counts[
            cluster_code
        ] += 1

        if classification[
            "significant"
        ]:

            significant_count += 1

        records.append(
            {

                "geography":
                    geography,

                "value":
                    _json_safe(
                        observed_value
                    ),

                "standardized_value":
                    standardized_value,

                "local_moran_i":
                    local_i,

                "pseudo_p_value":
                    pseudo_p_value,

                "p_value":
                    pseudo_p_value,

                "quadrant":
                    quadrant,

                "cluster_code":
                    cluster_code,

                "cluster_label":
                    classification[
                        "cluster_label"
                    ],

                "interpretation":
                    classification[
                        "interpretation"
                    ],

                "significant":
                    classification[
                        "significant"
                    ],

                "description":
                    classification[
                        "description"
                    ],

                "neighbor_count":
                    neighbor_count,

                "is_island":
                    bool(
                        is_island
                    ),
            }
        )

    # ========================================================
    # NEIGHBOR SUMMARY
    # ========================================================

    if neighbor_counts:

        mean_neighbors = float(
            np.mean(
                neighbor_counts
            )
        )

        minimum_neighbors = int(
            np.min(
                neighbor_counts
            )
        )

        maximum_neighbors = int(
            np.max(
                neighbor_counts
            )
        )

    else:

        mean_neighbors = 0.0

        minimum_neighbors = 0

        maximum_neighbors = 0

    # ========================================================
    # ANALYSIS SUMMARY
    # ========================================================

    summary = {

        "analysis_name":
            "Hotspot Analysis",

        "method":
            "Local Moran's I (LISA)",

        "software":
            "PySAL esda / libpysal",

        "spatial_weights":
            "Queen contiguity",

        "contiguity_setting":
            "rook=False",

        "weights_transformation":
            "Row-standardized",

        "inference_method":
            "Conditional random permutations",

        "significance_measure":
            "Permutation pseudo p-value (p_sim)",

        # Important:
        #
        # The supplied reference discusses the multiple
        # comparisons issue but does not apply an FDR or
        # Bonferroni correction in the demonstrated workflow.
        "multiple_testing_correction":
            "None",

        "geography_column":
            geography_column,

        "value_column":
            value_column,

        "observations":
            int(
                observation_count
            ),

        # Reference-derived value unless the user overrides it.
        "permutations":
            int(
                permutations
            ),

        # SENSD-selected classification threshold.
        "significance_level":
            float(
                significance_level
            ),

        # Reference-derived value unless the user overrides it.
        "random_seed":
            int(
                seed
            ),

        "significant_count":
            int(
                significant_count
            ),

        "not_significant_count":
            int(
                counts[
                    "NS"
                ]
            ),

        "hot_spot_count":
            int(
                counts[
                    "HH"
                ]
            ),

        "cold_spot_count":
            int(
                counts[
                    "LL"
                ]
            ),

        "high_value_outlier_count":
            int(
                counts[
                    "HL"
                ]
            ),

        "low_value_outlier_count":
            int(
                counts[
                    "LH"
                ]
            ),

        "high_high_count":
            int(
                counts[
                    "HH"
                ]
            ),

        "low_low_count":
            int(
                counts[
                    "LL"
                ]
            ),

        "high_low_count":
            int(
                counts[
                    "HL"
                ]
            ),

        "low_high_count":
            int(
                counts[
                    "LH"
                ]
            ),

        "island_count":
            int(
                counts[
                    "ISLAND"
                ]
            ),

        "mean_neighbors":
            _json_safe(
                mean_neighbors
            ),

        "minimum_neighbors":
            minimum_neighbors,

        "maximum_neighbors":
            maximum_neighbors,
    }

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "summary":
            summary,

        "records":
            records,
    }
