# ============================================================
# geosens/views.py
# ============================================================

import json
import math
from typing import Any

import numpy as np
import pandas as pd

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .analysis.bivariate import calculate_bivariate_map
from .analysis.local_moran import calculate_local_moran
from .analysis.salmonella import (
    calculate_county_risk,
    calculate_salmonella_risk_map,
)
from .analysis.spatial_association import (
    calculate_spatial_association,
)
from .analysis.spatial_regression import (
    calculate_spatial_regression,
)

from .models import (
    AnalysisRun,
    UploadedDataset,
    UploadedFeature,
)


# ============================================================
# PAGE VIEWS
# ============================================================

def home_view(request):
    return render(
        request,
        "home.html",
    )


def maps_view(request):
    return render(
        request,
        "maps.html",
    )


def grid_view(request):
    return render(
        request,
        "grid_view.html",
    )


def data_mapping_tool_view(request):
    return render(
        request,
        "data_mapping_tool.html",
    )


def flow_analysis_view(request):
    return render(
        request,
        "mapsapp/spatial_analysis.html",
        {
            "map_tile_config": {
                "url": settings.MAP_TILE_URL,
                "attribution": settings.MAP_TILE_ATTRIBUTION,
                "maxZoom": settings.MAP_TILE_MAX_ZOOM,
            }
        },
    )


# ============================================================
# JSON HELPERS
# ============================================================

def make_json_safe(value: Any) -> Any:
    """
    Recursively convert pandas / NumPy values into standard
    JSON-safe Python values.
    """

    if value is None:
        return None

    if isinstance(
        value,
        (np.bool_, bool),
    ):
        return bool(value)

    if isinstance(
        value,
        (np.integer, int),
    ):
        return int(value)

    if isinstance(
        value,
        (np.floating, float),
    ):
        number = float(value)

        if not math.isfinite(number):
            return None

        return number

    if isinstance(
        value,
        pd.Timestamp,
    ):
        return value.isoformat()

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): make_json_safe(item)
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        (list, tuple, set),
    ):
        return [
            make_json_safe(item)
            for item in value
        ]

    try:
        if pd.isna(value):
            return None

    except (
        TypeError,
        ValueError,
    ):
        pass

    return value


def encryptable_json_text(
    value: Any,
) -> str:
    """
    Serialize content for EncryptedTextField.
    """

    return json.dumps(
        make_json_safe(value),
        ensure_ascii=False,
    )


def decryptable_json_value(
    value: Any,
    default=None,
):
    """
    Decode JSON stored inside an encrypted text field.
    """

    if value in (
        None,
        "",
    ):
        return (
            default
            if default is not None
            else {}
        )

    if isinstance(
        value,
        (dict, list),
    ):
        return value

    try:
        return json.loads(
            value
        )

    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return (
            default
            if default is not None
            else {}
        )


# ============================================================
# FILE HELPERS
# ============================================================

def get_file_extension(
    filename: str,
) -> str:
    """
    Return normalized file extension without the period.
    """

    if not filename:
        return ""

    if "." not in filename:
        return ""

    return (
        filename
        .rsplit(".", 1)[-1]
        .lower()
        .strip()
    )


def read_uploaded_dataframe(
    uploaded_file,
) -> pd.DataFrame:
    """
    Read CSV or Excel into pandas.
    """

    extension = (
        get_file_extension(
            uploaded_file.name
        )
    )

    uploaded_file.seek(0)

    if extension == "csv":

        dataframe = pd.read_csv(
            uploaded_file
        )

    elif extension in (
        "xlsx",
        "xls",
    ):

        dataframe = pd.read_excel(
            uploaded_file
        )

    else:

        raise ValueError(
            "Only CSV or Excel files are supported "
            "for tabular uploads."
        )

    uploaded_file.seek(0)

    return dataframe


def read_uploaded_geojson(
    uploaded_file,
) -> dict:
    """
    Read GeoJSON / JSON upload.
    """

    extension = (
        get_file_extension(
            uploaded_file.name
        )
    )

    if extension not in (
        "geojson",
        "json",
    ):
        raise ValueError(
            "A GeoJSON or JSON file is required."
        )

    uploaded_file.seek(0)

    raw_content = (
        uploaded_file.read()
    )

    uploaded_file.seek(0)

    if isinstance(
        raw_content,
        bytes,
    ):
        raw_content = (
            raw_content.decode(
                "utf-8-sig"
            )
        )

    try:
        data = json.loads(
            raw_content
        )

    except json.JSONDecodeError as exc:
        raise ValueError(
            "The uploaded file is not valid JSON."
        ) from exc

    if (
        not isinstance(
            data,
            dict,
        )
        or data.get("type")
        != "FeatureCollection"
    ):
        raise ValueError(
            "The uploaded file must be a GeoJSON "
            "FeatureCollection."
        )

    if not isinstance(
        data.get("features"),
        list,
    ):
        raise ValueError(
            "GeoJSON FeatureCollection does not contain "
            "a valid features array."
        )

    return data


# ============================================================
# GEOJSON HELPERS
# ============================================================

def get_geojson_geometry_type(
    geojson_data: dict,
) -> str:
    """
    Return first available geometry type.
    """

    for feature in (
        geojson_data.get("features")
        or []
    ):

        geometry = (
            feature.get("geometry")
            or {}
        )

        geometry_type = (
            geometry.get("type")
        )

        if geometry_type:
            return str(
                geometry_type
            )

    return "Unknown"


def get_geojson_fields(
    geojson_data: dict,
) -> list[str]:
    """
    Return all property field names.
    """

    fields = set()

    for feature in (
        geojson_data.get("features")
        or []
    ):

        properties = (
            feature.get("properties")
            or {}
        )

        fields.update(
            properties.keys()
        )

    return sorted(
        str(field)
        for field in fields
    )


def dataframe_row_to_properties(
    row: pd.Series,
) -> dict:
    """
    Convert pandas row into JSON-safe properties.
    """

    properties = {}

    for column, value in (
        row.to_dict().items()
    ):

        properties[
            str(column)
        ] = make_json_safe(
            value
        )

    return properties


def validate_polygon_geojson(
    geojson_data: dict,
) -> None:
    """
    Ensure polygon geometry for polygon-based analyses.
    """

    if (
        geojson_data.get("type")
        != "FeatureCollection"
    ):
        raise ValueError(
            "A GeoJSON FeatureCollection is required."
        )

    features = (
        geojson_data.get("features")
        or []
    )

    if not features:
        raise ValueError(
            "The GeoJSON dataset contains no features."
        )

    valid_geometry_found = False

    for feature in features:

        geometry = (
            feature.get("geometry")
        )

        if not geometry:
            continue

        geometry_type = (
            geometry.get("type")
        )

        if geometry_type not in (
            "Polygon",
            "MultiPolygon",
        ):
            raise ValueError(
                "This analysis requires Polygon or "
                "MultiPolygon geometry."
            )

        valid_geometry_found = True

    if not valid_geometry_found:
        raise ValueError(
            "No valid polygon geometries were found."
        )


def clean_geography_value(
    value: Any,
) -> str:
    """
    Normalize geographic identifier.
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""

    except (
        TypeError,
        ValueError,
    ):
        pass

    return str(value).strip()


def geography_lookup_key(value: Any) -> str:
    """Match geography IDs using their cleaned, case-sensitive value."""
    return clean_geography_value(value)


# ============================================================
# DATABASE PERSISTENCE
# ============================================================

def save_geojson_dataset(
    *,
    owner,
    geojson_data: dict,
    dataset_name: str,
    original_filename: str,
    file_type: str = "GeoJSON",
) -> UploadedDataset:
    """
    Persist GeoJSON into PostgreSQL/PostGIS.

    Geometry remains queryable in PostGIS.
    Attribute properties remain encrypted.
    """

    fields = (
        get_geojson_fields(
            geojson_data
        )
    )

    geometry_type = (
        get_geojson_geometry_type(
            geojson_data
        )
    )

    features = (
        geojson_data.get("features")
        or []
    )

    dataset = (
        UploadedDataset.objects.create(
            owner=owner,
            name=dataset_name,
            original_filename=
                original_filename,
            fields=
                encryptable_json_text(
                    fields
                ),
            file_type=
                file_type,
            geometry_type=
                geometry_type,
            feature_count=
                len(features),
        )
    )

    database_features = []

    for feature in features:

        geometry_data = (
            feature.get("geometry")
        )

        if not geometry_data:
            continue

        try:
            geometry = GEOSGeometry(
                json.dumps(
                    geometry_data
                ),
                srid=4326,
            )

        except Exception:
            continue

        properties = (
            feature.get("properties")
            or {}
        )

        database_features.append(
            UploadedFeature(
                dataset=dataset,
                geometry=geometry,
                properties=
                    encryptable_json_text(
                        properties
                    ),
            )
        )

    if database_features:

        UploadedFeature.objects.bulk_create(
            database_features
        )

    return dataset


def save_analysis_run(
    *,
    dataset: UploadedDataset,
    analysis_type: str,
    parameters: dict,
    summary: dict,
) -> AnalysisRun:
    """
    Save encrypted analysis parameters and summary.
    """

    return (
        AnalysisRun.objects.create(
            dataset=dataset,
            analysis_type=
                analysis_type,
            parameters=
                encryptable_json_text(
                    parameters
                ),
            summary=
                encryptable_json_text(
                    summary
                ),
        )
    )


# ============================================================
# FILE FIELD INSPECTION
# ============================================================

@require_http_methods(["POST"])
def inspect_columns_api(request):

    try:

        uploaded_file = (
            request.FILES.get("file")
        )

        if not uploaded_file:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "No file received.",
                },
                status=400,
            )

        extension = (
            get_file_extension(
                uploaded_file.name
            )
        )

        if extension in (
            "csv",
            "xlsx",
            "xls",
        ):

            dataframe = (
                read_uploaded_dataframe(
                    uploaded_file
                )
            )

            return JsonResponse(
                {
                    "success": True,
                    "filename":
                        uploaded_file.name,
                    "file_type":
                        extension,
                    "columns": [
                        str(column)
                        for column
                        in dataframe.columns
                    ],
                    "row_count":
                        len(dataframe),
                }
            )

        if extension in (
            "geojson",
            "json",
        ):

            geojson_data = (
                read_uploaded_geojson(
                    uploaded_file
                )
            )

            return JsonResponse(
                {
                    "success": True,
                    "filename":
                        uploaded_file.name,
                    "file_type":
                        extension,
                    "columns":
                        get_geojson_fields(
                            geojson_data
                        ),
                    "row_count":
                        len(
                            geojson_data.get(
                                "features"
                            )
                            or []
                        ),
                    "geometry_type":
                        get_geojson_geometry_type(
                            geojson_data
                        ),
                }
            )

        return JsonResponse(
            {
                "success": False,
                "error":
                    "Unsupported file format. "
                    "Use CSV, Excel, GeoJSON, or JSON.",
            },
            status=415,
        )

    except Exception as exc:

        print(
            "inspect_columns_api error:",
            exc,
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )


# ============================================================
# FLOW UPLOAD
# ============================================================

@require_http_methods(["POST"])
def upload_flow_api(request):

    try:

        uploaded_file = (
            request.FILES.get("file")
        )

        if not uploaded_file:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "No file received.",
                },
                status=400,
            )

        extension = (
            get_file_extension(
                uploaded_file.name
            )
        )

        if extension not in (
            "csv",
            "xlsx",
            "xls",
        ):

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Flow Data supports CSV or Excel.",
                },
                status=415,
            )

        dataframe = (
            read_uploaded_dataframe(
                uploaded_file
            )
        )

        mapping = {

            "from_id":
                request.POST.get(
                    "from_id",
                    "",
                ),

            "from_node":
                request.POST.get(
                    "from_node",
                    "",
                ),

            "from_city_area":
                request.POST.get(
                    "from_city_area",
                    "",
                ),

            "from_state":
                request.POST.get(
                    "from_state",
                    "",
                ),

            "from_latitude":
                request.POST.get(
                    "from_latitude",
                    "",
                ),

            "from_longitude":
                request.POST.get(
                    "from_longitude",
                    "",
                ),

            "to_id":
                request.POST.get(
                    "to_id",
                    "",
                ),

            "to_node":
                request.POST.get(
                    "to_node",
                    "",
                ),

            "to_city_area":
                request.POST.get(
                    "to_city_area",
                    "",
                ),

            "to_state":
                request.POST.get(
                    "to_state",
                    "",
                ),

            "to_latitude":
                request.POST.get(
                    "to_latitude",
                    "",
                ),

            "to_longitude":
                request.POST.get(
                    "to_longitude",
                    "",
                ),

            "quantity":
                request.POST.get(
                    "quantity",
                    "",
                ),

            "product_type_i":
                request.POST.get(
                    "product_type_i",
                    "",
                ),

            "product_type_j":
                request.POST.get(
                    "product_type_j",
                    "",
                ),
        }

        required_mappings = [
            "from_id",
            "from_latitude",
            "from_longitude",
            "to_id",
            "to_latitude",
            "to_longitude",
            "quantity",
        ]

        missing_mapping = [
            key
            for key
            in required_mappings
            if not mapping.get(key)
        ]

        if missing_mapping:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Missing required flow field mapping: "
                        + ", ".join(
                            missing_mapping
                        ),
                },
                status=400,
            )

        selected_columns = [
            column
            for column
            in mapping.values()
            if column
        ]

        missing_columns = [
            column
            for column
            in selected_columns
            if column not in dataframe.columns
        ]

        if missing_columns:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Mapped fields were not found: "
                        + ", ".join(
                            missing_columns
                        ),
                },
                status=400,
            )

        def row_value(
            row,
            mapping_key,
            default="",
        ):

            column = (
                mapping.get(
                    mapping_key
                )
            )

            if not column:
                return default

            value = row.get(
                column
            )

            if pd.isna(value):
                return default

            return value

        features = []

        for _, row in (
            dataframe.iterrows()
        ):

            try:

                from_latitude = float(
                    row_value(
                        row,
                        "from_latitude",
                    )
                )

                from_longitude = float(
                    row_value(
                        row,
                        "from_longitude",
                    )
                )

                to_latitude = float(
                    row_value(
                        row,
                        "to_latitude",
                    )
                )

                to_longitude = float(
                    row_value(
                        row,
                        "to_longitude",
                    )
                )

                quantity = float(
                    row_value(
                        row,
                        "quantity",
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

            numeric_values = (
                from_latitude,
                from_longitude,
                to_latitude,
                to_longitude,
                quantity,
            )

            if not all(
                math.isfinite(value)
                for value
                in numeric_values
            ):
                continue

            properties = (
                dataframe_row_to_properties(
                    row
                )
            )

            properties.update(
                {
                    "from_id":
                        str(
                            row_value(
                                row,
                                "from_id",
                            )
                        ),

                    "from_node":
                        str(
                            row_value(
                                row,
                                "from_node",
                            )
                        ),

                    "from_city_area":
                        str(
                            row_value(
                                row,
                                "from_city_area",
                            )
                        ),

                    "from_state":
                        str(
                            row_value(
                                row,
                                "from_state",
                            )
                        ),

                    "from_latitude":
                        from_latitude,

                    "from_longitude":
                        from_longitude,

                    "to_id":
                        str(
                            row_value(
                                row,
                                "to_id",
                            )
                        ),

                    "to_node":
                        str(
                            row_value(
                                row,
                                "to_node",
                            )
                        ),

                    "to_city_area":
                        str(
                            row_value(
                                row,
                                "to_city_area",
                            )
                        ),

                    "to_state":
                        str(
                            row_value(
                                row,
                                "to_state",
                            )
                        ),

                    "to_latitude":
                        to_latitude,

                    "to_longitude":
                        to_longitude,

                    "quantity":
                        quantity,

                    "product_type_i":
                        str(
                            row_value(
                                row,
                                "product_type_i",
                            )
                        ).strip(),

                    "product_type_j":
                        str(
                            row_value(
                                row,
                                "product_type_j",
                            )
                        ).strip(),
                }
            )

            features.append(
                {
                    "type": "Feature",

                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            from_longitude,
                            from_latitude,
                        ],
                    },

                    "properties":
                        properties,
                }
            )

        if not features:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "No valid flow rows were found.",
                },
                status=400,
            )

        geojson_data = {
            "type":
                "FeatureCollection",
            "features":
                features,
        }

        dataset = (
            save_geojson_dataset(
                owner=request.user,
                geojson_data=
                    geojson_data,
                dataset_name=
                    uploaded_file.name,
                original_filename=
                    uploaded_file.name,
                file_type=
                    extension.upper(),
            )
        )

        return JsonResponse(
            {
                "success": True,
                "filename":
                    uploaded_file.name,
                "rows_loaded":
                    len(features),
                "dataset_id":
                    dataset.id,
                "geojson":
                    make_json_safe(
                        geojson_data
                    ),
            }
        )

    except Exception as exc:

        print(
            "upload_flow_api error:",
            exc,
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )


# ============================================================
# DATA LAYER UPLOAD
# ============================================================

@require_http_methods(["POST"])
def upload_reference_api(request):

    try:

        uploaded_file = (
            request.FILES.get("file")
        )

        if not uploaded_file:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "No file received.",
                },
                status=400,
            )

        extension = (
            get_file_extension(
                uploaded_file.name
            )
        )

        if extension in (
            "csv",
            "xlsx",
            "xls",
        ):

            dataframe = (
                read_uploaded_dataframe(
                    uploaded_file
                )
            )

            latitude_column = (
                request.POST.get(
                    "lat_column",
                    "",
                )
            )

            longitude_column = (
                request.POST.get(
                    "lng_column",
                    "",
                )
            )

            if not (
                latitude_column
                and longitude_column
            ):

                return JsonResponse(
                    {
                        "success": False,
                        "error":
                            "Latitude and longitude fields "
                            "are required.",
                    },
                    status=400,
                )

            if (
                latitude_column
                not in dataframe.columns
                or longitude_column
                not in dataframe.columns
            ):

                return JsonResponse(
                    {
                        "success": False,
                        "error":
                            "Selected coordinate fields "
                            "were not found.",
                    },
                    status=400,
                )

            features = []

            for _, row in (
                dataframe.iterrows()
            ):

                try:

                    latitude = float(
                        row[
                            latitude_column
                        ]
                    )

                    longitude = float(
                        row[
                            longitude_column
                        ]
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                if not (
                    math.isfinite(
                        latitude
                    )
                    and math.isfinite(
                        longitude
                    )
                ):
                    continue

                features.append(
                    {
                        "type":
                            "Feature",

                        "geometry": {
                            "type":
                                "Point",
                            "coordinates": [
                                longitude,
                                latitude,
                            ],
                        },

                        "properties":
                            dataframe_row_to_properties(
                                row
                            ),
                    }
                )

            geojson_data = {
                "type":
                    "FeatureCollection",
                "features":
                    features,
            }

        elif extension in (
            "geojson",
            "json",
        ):

            geojson_data = (
                read_uploaded_geojson(
                    uploaded_file
                )
            )

            features = (
                geojson_data.get(
                    "features"
                )
                or []
            )

        else:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Unsupported format. Use CSV, Excel, "
                        "GeoJSON, or JSON.",
                },
                status=415,
            )

        if not features:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "No valid geographic features found.",
                },
                status=400,
            )

        dataset = (
            save_geojson_dataset(
                owner=request.user,
                geojson_data=
                    geojson_data,
                dataset_name=
                    uploaded_file.name,
                original_filename=
                    uploaded_file.name,
                file_type=
                    extension.upper(),
            )
        )

        return JsonResponse(
            {
                "success": True,
                "filename":
                    uploaded_file.name,
                "feature_count":
                    len(features),
                "dataset_id":
                    dataset.id,
                "geometry_type":
                    get_geojson_geometry_type(
                        geojson_data
                    ),
                "geojson":
                    make_json_safe(
                        geojson_data
                    ),
            }
        )

    except Exception as exc:

        print(
            "upload_reference_api error:",
            exc,
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )


# ============================================================
# RISK MAP
# ============================================================

@require_http_methods(["POST"])
def salmonella_risk_map_api(request):

    try:

        uploaded_file = (
            request.FILES.get("file")
        )

        geography_column = (
            request.POST.get(
                "geography_column",
                "",
            ).strip()
        )

        cases_column = (
            request.POST.get(
                "cases_column",
                "",
            ).strip()
        )

        population_column = (
            request.POST.get(
                "population_column",
                "",
            ).strip()
        )

        if not uploaded_file:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "No analysis file received.",
                },
                status=400,
            )

        if not all(
            [
                geography_column,
                cases_column,
                population_column,
            ]
        ):

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Geography, cases, and population "
                        "fields are required.",
                },
                status=400,
            )

        geojson_data = (
            read_uploaded_geojson(
                uploaded_file
            )
        )

        validate_polygon_geojson(
            geojson_data
        )

        fields = (
            get_geojson_fields(
                geojson_data
            )
        )

        required_fields = [
            geography_column,
            cases_column,
            population_column,
        ]

        missing_fields = [
            field
            for field
            in required_fields
            if field not in fields
        ]

        if missing_fields:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Selected fields were not found: "
                        + ", ".join(
                            missing_fields
                        ),
                },
                status=400,
            )

        dataframe_records = []

        for feature in (
            geojson_data.get(
                "features"
            )
            or []
        ):

            properties = (
                feature.get(
                    "properties"
                )
                or {}
            )

            dataframe_records.append(
                properties
            )

        if not dataframe_records:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "No attribute records were found "
                        "in the uploaded GeoJSON.",
                },
                status=400,
            )

        dataframe = pd.DataFrame(
            dataframe_records
        )

        analysis = (
            calculate_salmonella_risk_map(
                dataframe,
                geography_column=
                    geography_column,
                cases_column=
                    cases_column,
                population_column=
                    population_column,
            )
        )

        summary = (
            analysis.get("summary")
            or {}
        )

        records = (
            analysis.get("records")
            or []
        )

        lookup = {
            geography_lookup_key(
                record.get(
                    "geography"
                )
            ):
                record
            for record
            in records
        }

        analyzed_geojson = (
            json.loads(
                json.dumps(
                    geojson_data
                )
            )
        )

        for feature in (
            analyzed_geojson.get(
                "features"
            )
            or []
        ):

            properties = (
                feature.setdefault(
                    "properties",
                    {},
                )
            )

            key = (
                geography_lookup_key(
                    properties.get(
                        geography_column
                    )
                )
            )

            record = (
                lookup.get(
                    key
                )
            )

            if not record:

                properties.update(
                    {
                        "sensd_salmonella_cases":
                            None,

                        "sensd_population":
                            None,

                        "sensd_salmonella_rate":
                            None,

                        "sensd_percentile":
                            None,

                        "sensd_risk_level":
                            "No Data",

                        "sensd_risk_class":
                            None,
                    }
                )

                continue

            properties.update(
                {
                    "sensd_salmonella_cases":
                        record.get(
                            "cases"
                        ),

                    "sensd_population":
                        record.get(
                            "population"
                        ),

                    "sensd_salmonella_rate":
                        record.get(
                            "rate_per_100k"
                        ),

                    "sensd_percentile":
                        record.get(
                            "percentile"
                        ),

                    "sensd_risk_level":
                        record.get(
                            "risk_level"
                        ),

                    "sensd_risk_class":
                        record.get(
                            "risk_class"
                        ),
                }
            )

        dataset = (
            save_geojson_dataset(
                owner=request.user,
                geojson_data=
                    geojson_data,
                dataset_name=
                    uploaded_file.name,
                original_filename=
                    uploaded_file.name,
                file_type=
                    "GeoJSON",
            )
        )

        analysis_run = (
            save_analysis_run(
                dataset=
                    dataset,
                analysis_type=
                    "salmonella_risk",
                parameters={
                    "analysis_name":
                        "Risk Map",

                    "method":
                        "Rate per 100,000 with percentile-based "
                        "relative risk classification",

                    "geography_column":
                        geography_column,

                    "cases_column":
                        cases_column,

                    "population_column":
                        population_column,

                    "rate_formula":
                        "cases / population * 100000",

                    "classification":
                        "Percentile-based relative risk",
                },
                summary=
                    summary,
            )
        )

        return JsonResponse(
            {
                "success": True,

                "filename":
                    uploaded_file.name,

                "dataset_id":
                    dataset.id,

                "analysis_run_id":
                    analysis_run.id,

                "geography_column":
                    geography_column,

                "cases_column":
                    cases_column,

                "population_column":
                    population_column,

                "summary":
                    make_json_safe(
                        summary
                    ),

                "records":
                    make_json_safe(
                        records
                    ),

                "geojson":
                    make_json_safe(
                        analyzed_geojson
                    ),
            }
        )

    except ValueError as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )

    except Exception as exc:

        print(
            "salmonella_risk_map_api error:",
            exc,
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )


# ============================================================
# BIVARIATE ANALYSIS
# ============================================================

@require_http_methods(["POST"])
def bivariate_map_api(request):

    try:

        # ====================================================
        # INPUTS
        # ====================================================

        uploaded_file = (
            request.FILES.get("file")
        )

        geography_column = (
            request.POST.get(
                "geography_column",
                "",
            ).strip()
        )

        state_column = (
            request.POST.get(
                "state_column",
                "",
            ).strip()
        )

        county_column = (
            request.POST.get(
                "county_column",
                "",
            ).strip()
        )

        x_column = (
            request.POST.get(
                "x_column",
                "",
            ).strip()
        )

        y_column = (
            request.POST.get(
                "y_column",
                "",
            ).strip()
        )

        # ====================================================
        # BASIC VALIDATION
        # ====================================================

        if not uploaded_file:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "No analysis file received.",
                },
                status=400,
            )

        if not all(
            [
                geography_column,
                x_column,
                y_column,
            ]
        ):

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Geography, Variable X, and Variable Y "
                        "are required.",
                },
                status=400,
            )

        if x_column == y_column:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Variable X and Variable Y must "
                        "be different.",
                },
                status=400,
            )

        # ====================================================
        # READ GEOJSON
        # ====================================================

        geojson_data = (
            read_uploaded_geojson(
                uploaded_file
            )
        )

        validate_polygon_geojson(
            geojson_data
        )

        # ====================================================
        # VALIDATE SELECTED FIELDS
        # ====================================================

        fields = (
            get_geojson_fields(
                geojson_data
            )
        )

        required_fields = [
            geography_column,
            x_column,
            y_column,
        ]

        if state_column:
            required_fields.append(
                state_column
            )

        if county_column:
            required_fields.append(
                county_column
            )

        missing_fields = [
            field
            for field
            in required_fields
            if field not in fields
        ]

        if missing_fields:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Selected fields were not found: "
                        + ", ".join(
                            missing_fields
                        ),
                },
                status=400,
            )

        # ====================================================
        # CONVERT GEOJSON PROPERTIES TO DATAFRAME
        # ====================================================

        dataframe_records = []

        for feature in (
            geojson_data.get(
                "features"
            )
            or []
        ):

            properties = (
                feature.get(
                    "properties"
                )
                or {}
            )

            dataframe_records.append(
                properties
            )

        if not dataframe_records:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "No attribute records were found "
                        "in the uploaded GeoJSON.",
                },
                status=400,
            )

        dataframe = pd.DataFrame(
            dataframe_records
        )

        # ====================================================
        # RUN BIVARIATE ANALYSIS
        # ====================================================

        analysis = (
            calculate_bivariate_map(
                dataframe,
                geography_column=
                    geography_column,
                x_column=
                    x_column,
                y_column=
                    y_column,
            )
        )

        summary = (
            analysis.get("summary")
            or {}
        )

        records = (
            analysis.get("records")
            or []
        )

        # ====================================================
        # RESULT LOOKUP
        # ====================================================

        lookup = {
            geography_lookup_key(
                record.get(
                    "geography"
                )
            ):
                record

            for record
            in records
        }

        # ====================================================
        # COPY GEOJSON FOR MAP RESULT
        # ====================================================

        analyzed_geojson = (
            json.loads(
                json.dumps(
                    geojson_data
                )
            )
        )

        # ====================================================
        # ATTACH BIVARIATE RESULTS TO FEATURES
        # ====================================================

        for feature in (
            analyzed_geojson.get(
                "features"
            )
            or []
        ):

            properties = (
                feature.setdefault(
                    "properties",
                    {},
                )
            )

            key = (
                geography_lookup_key(
                    properties.get(
                        geography_column
                    )
                )
            )

            record = (
                lookup.get(
                    key
                )
            )

            # ------------------------------------------------
            # OPTIONAL DISPLAY FIELDS
            # ------------------------------------------------

            properties[
                "sensd_state_name"
            ] = (
                make_json_safe(
                    properties.get(
                        state_column
                    )
                )
                if state_column
                else None
            )

            properties[
                "sensd_county_name"
            ] = (
                make_json_safe(
                    properties.get(
                        county_column
                    )
                )
                if county_column
                else None
            )

            # ------------------------------------------------
            # NO MATCH / EXCLUDED FEATURE
            # ------------------------------------------------

            if not record:

                properties.update(
                    {
                        "sensd_bivariate_x_value":
                            None,

                        "sensd_bivariate_y_value":
                            None,

                        "sensd_bivariate_x_class":
                            None,

                        "sensd_bivariate_y_class":
                            None,

                        "sensd_bivariate_x_level":
                            None,

                        "sensd_bivariate_y_level":
                            None,

                        "sensd_bivariate_class":
                            "no_data",

                        "sensd_bivariate_class_number":
                            None,

                        "sensd_bivariate_label":
                            "No Data",
                    }
                )

                continue

            # ------------------------------------------------
            # VALID BIVARIATE RESULT
            # ------------------------------------------------

            properties.update(
                {
                    "sensd_bivariate_x_value":
                        record.get(
                            "x_value"
                        ),

                    "sensd_bivariate_y_value":
                        record.get(
                            "y_value"
                        ),

                    "sensd_bivariate_x_class":
                        record.get(
                            "x_class"
                        ),

                    "sensd_bivariate_y_class":
                        record.get(
                            "y_class"
                        ),

                    "sensd_bivariate_x_level":
                        record.get(
                            "x_level"
                        ),

                    "sensd_bivariate_y_level":
                        record.get(
                            "y_level"
                        ),

                    "sensd_bivariate_class":
                        record.get(
                            "bivariate_class"
                        ),

                    "sensd_bivariate_class_number":
                        record.get(
                            "bivariate_class_number"
                        ),

                    "sensd_bivariate_label":
                        record.get(
                            "bivariate_label"
                        ),
                }
            )

        # ====================================================
        # SAVE ORIGINAL DATASET
        # ====================================================

        dataset = (
            save_geojson_dataset(
                owner=request.user,
                geojson_data=
                    geojson_data,

                dataset_name=
                    uploaded_file.name,

                original_filename=
                    uploaded_file.name,

                file_type=
                    "GeoJSON",
            )
        )

        # ====================================================
        # SAVE ANALYSIS RUN
        # ====================================================

        analysis_run = (
            save_analysis_run(
                dataset=
                    dataset,

                analysis_type=
                    "bivariate",

                parameters={
                    "analysis_name":
                        "Bivariate Analysis",

                    "method":
                        "3 x 3 relative bivariate "
                        "tertile classification",

                    "geography_column":
                        geography_column,

                    "state_column":
                        state_column or None,

                    "county_column":
                        county_column or None,

                    "x_column":
                        x_column,

                    "y_column":
                        y_column,

                    "classification":
                        "Percentile-ranked Low / Medium / High "
                        "classes for X and Y",

                    "spatial_statistic":
                        False,
                },

                summary=
                    summary,
            )
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        return JsonResponse(
            {
                "success":
                    True,

                "filename":
                    uploaded_file.name,

                "dataset_id":
                    dataset.id,

                "analysis_run_id":
                    analysis_run.id,

                "analysis_name":
                    "Bivariate Analysis",

                "method":
                    "3 x 3 relative bivariate "
                    "tertile classification",

                "geography_column":
                    geography_column,

                "x_column":
                    x_column,

                "y_column":
                    y_column,

                "summary":
                    make_json_safe(
                        summary
                    ),

                "records":
                    make_json_safe(
                        records
                    ),

                "geojson":
                    make_json_safe(
                        analyzed_geojson
                    ),
            }
        )

    except ValueError as exc:

        return JsonResponse(
            {
                "success": False,
                "error":
                    str(exc),
            },
            status=400,
        )

    except Exception as exc:

        print(
            "bivariate_map_api error:",
            exc,
        )

        return JsonResponse(
            {
                "success": False,
                "error":
                    str(exc),
            },
            status=500,
        )

# ============================================================
# LOCAL MORAN'S I
# ============================================================

@require_http_methods(["POST"])
def local_moran_api(request):

    try:

        uploaded_file = (
            request.FILES.get("file")
        )

        geography_column = (
            request.POST.get(
                "geography_column",
                "",
            ).strip()
        )

        state_column = (
            request.POST.get(
                "state_column",
                "",
            ).strip()
        )

        county_column = (
            request.POST.get(
                "county_column",
                "",
            ).strip()
        )

        value_column = (
            request.POST.get(
                "value_column",
                "",
            ).strip()
        )

        permutations_raw = (
            request.POST.get(
                "permutations",
                "",
            ).strip()
        )

        significance_raw = (
            request.POST.get(
                "significance_level",
                "",
            ).strip()
        )

        seed_raw = (
            request.POST.get(
                "seed",
                "",
            ).strip()
        )

        if not uploaded_file:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "No analysis file received.",
                },
                status=400,
            )

        if not (
            geography_column
            and value_column
        ):

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Geography Field and Analysis Variable "
                        "are required.",
                },
                status=400,
            )

        geojson_data = (
            read_uploaded_geojson(
                uploaded_file
            )
        )

        validate_polygon_geojson(
            geojson_data
        )

        kwargs = {
            "geojson_data":
                geojson_data,
            "geography_column":
                geography_column,
            "value_column":
                value_column,
        }

        if permutations_raw:
            kwargs["permutations"] = int(
                permutations_raw
            )

        if significance_raw:
            kwargs[
                "significance_level"
            ] = float(
                significance_raw
            )

        if seed_raw:
            kwargs["seed"] = int(
                seed_raw
            )

        analysis = (
            calculate_local_moran(
                **kwargs
            )
        )

        summary = (
            analysis.get("summary")
            or {}
        )

        records = (
            analysis.get("records")
            or []
        )

        lookup = {
            geography_lookup_key(
                record.get("geography")
            ):
                record
            for record
            in records
        }

        analyzed_geojson = (
            json.loads(
                json.dumps(
                    geojson_data
                )
            )
        )

        for feature in (
            analyzed_geojson.get(
                "features"
            )
            or []
        ):

            properties = (
                feature.setdefault(
                    "properties",
                    {},
                )
            )

            key = (
                geography_lookup_key(
                    properties.get(
                        geography_column
                    )
                )
            )

            record = (
                lookup.get(key)
            )

            properties[
                "sensd_state_name"
            ] = (
                make_json_safe(
                    properties.get(
                        state_column
                    )
                )
                if state_column
                else None
            )

            properties[
                "sensd_county_name"
            ] = (
                make_json_safe(
                    properties.get(
                        county_column
                    )
                )
                if county_column
                else None
            )

            if not record:

                properties.update(
                    {
                        "sensd_local_moran_value":
                            None,
                        "sensd_local_moran_z":
                            None,
                        "sensd_local_moran_i":
                            None,
                        "sensd_local_moran_p":
                            None,
                        "sensd_local_moran_quadrant":
                            None,
                        "sensd_local_moran_cluster_code":
                            "NO_DATA",
                        "sensd_local_moran_cluster_label":
                            "No Data",
                        "sensd_local_moran_interpretation":
                            "No Data",
                        "sensd_local_moran_significant":
                            False,
                        "sensd_local_moran_neighbor_count":
                            None,
                        "sensd_local_moran_island":
                            False,
                        "sensd_local_moran_description":
                            "Feature excluded from analysis.",
                    }
                )

                continue

            properties.update(
                {
                    "sensd_local_moran_value":
                        record.get(
                            "value"
                        ),

                    "sensd_local_moran_z":
                        record.get(
                            "standardized_value"
                        ),

                    "sensd_local_moran_i":
                        record.get(
                            "local_moran_i"
                        ),

                    "sensd_local_moran_p":
                        (
                            record.get(
                                "pseudo_p_value"
                            )
                            if record.get(
                                "pseudo_p_value"
                            )
                            is not None
                            else record.get(
                                "p_value"
                            )
                        ),

                    "sensd_local_moran_quadrant":
                        record.get(
                            "quadrant"
                        ),

                    "sensd_local_moran_cluster_code":
                        record.get(
                            "cluster_code"
                        ),

                    "sensd_local_moran_cluster_label":
                        record.get(
                            "cluster_label"
                        ),

                    "sensd_local_moran_interpretation":
                        record.get(
                            "interpretation"
                        ),

                    "sensd_local_moran_significant":
                        bool(
                            record.get(
                                "significant",
                                False,
                            )
                        ),

                    "sensd_local_moran_neighbor_count":
                        record.get(
                            "neighbor_count"
                        ),

                    "sensd_local_moran_island":
                        bool(
                            record.get(
                                "is_island",
                                False,
                            )
                        ),

                    "sensd_local_moran_description":
                        record.get(
                            "description"
                        ),
                }
            )

        dataset = (
            save_geojson_dataset(
                owner=request.user,
                geojson_data=
                    geojson_data,
                dataset_name=
                    uploaded_file.name,
                original_filename=
                    uploaded_file.name,
                file_type=
                    "GeoJSON",
            )
        )

        analysis_run = (
            save_analysis_run(
                dataset=
                    dataset,
                analysis_type=
                    "local_moran",
                parameters={
                    "analysis_name":
                        "Hotspot Analysis",
                    "method":
                        "Local Moran's I (LISA)",
                    "geography_column":
                        geography_column,
                    "value_column":
                        value_column,
                    "state_column":
                        state_column or None,
                    "county_column":
                        county_column or None,
                    "spatial_weights":
                        "Queen contiguity",
                    "weight_transformation":
                        "Row-standardized",
                },
                summary=
                    summary,
            )
        )

        return JsonResponse(
            {
                "success": True,
                "filename":
                    uploaded_file.name,
                "dataset_id":
                    dataset.id,
                "analysis_run_id":
                    analysis_run.id,
                "value_column":
                    value_column,
                "summary":
                    make_json_safe(
                        summary
                    ),
                "records":
                    make_json_safe(
                        records
                    ),
                "geojson":
                    make_json_safe(
                        analyzed_geojson
                    ),
            }
        )

    except ValueError as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )

    except Exception as exc:

        print(
            "local_moran_api error:",
            exc,
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )


# ============================================================
# SPATIAL ASSOCIATION ANALYSIS
# ============================================================

@require_http_methods(["POST"])
def spatial_association_api(request):

    try:

        uploaded_file = (
            request.FILES.get("file")
        )

        geography_column = (
            request.POST.get(
                "geography_column",
                "",
            ).strip()
        )

        state_column = (
            request.POST.get(
                "state_column",
                "",
            ).strip()
        )

        county_column = (
            request.POST.get(
                "county_column",
                "",
            ).strip()
        )

        x_column = (
            request.POST.get(
                "x_column",
                "",
            ).strip()
        )

        y_column = (
            request.POST.get(
                "y_column",
                "",
            ).strip()
        )

        permutations_raw = (
            request.POST.get(
                "permutations",
                "",
            ).strip()
        )

        significance_raw = (
            request.POST.get(
                "significance_level",
                "",
            ).strip()
        )

        seed_raw = (
            request.POST.get(
                "seed",
                "",
            ).strip()
        )

        if not uploaded_file:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "No analysis file received.",
                },
                status=400,
            )

        if not all(
            [
                geography_column,
                x_column,
                y_column,
            ]
        ):

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Geography Field, Variable X, and "
                        "Variable Y are required.",
                },
                status=400,
            )

        if x_column == y_column:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Variable X and Variable Y "
                        "must be different.",
                },
                status=400,
            )

        geojson_data = (
            read_uploaded_geojson(
                uploaded_file
            )
        )

        validate_polygon_geojson(
            geojson_data
        )

        kwargs = {
            "geojson_data":
                geojson_data,
            "geography_column":
                geography_column,
            "x_column":
                x_column,
            "y_column":
                y_column,
        }

        if permutations_raw:
            kwargs[
                "permutations"
            ] = int(
                permutations_raw
            )

        if significance_raw:
            kwargs[
                "significance_level"
            ] = float(
                significance_raw
            )

        if seed_raw:
            kwargs["seed"] = int(
                seed_raw
            )

        analysis = (
            calculate_spatial_association(
                **kwargs
            )
        )

        summary = (
            analysis.get("summary")
            or {}
        )

        records = (
            analysis.get("records")
            or []
        )

        lookup = {
            geography_lookup_key(
                record.get("geography")
            ):
                record
            for record
            in records
        }

        analyzed_geojson = (
            json.loads(
                json.dumps(
                    geojson_data
                )
            )
        )

        for feature in (
            analyzed_geojson.get(
                "features"
            )
            or []
        ):

            properties = (
                feature.setdefault(
                    "properties",
                    {},
                )
            )

            key = (
                geography_lookup_key(
                    properties.get(
                        geography_column
                    )
                )
            )

            record = (
                lookup.get(key)
            )

            properties[
                "sensd_state_name"
            ] = (
                make_json_safe(
                    properties.get(
                        state_column
                    )
                )
                if state_column
                else None
            )

            properties[
                "sensd_county_name"
            ] = (
                make_json_safe(
                    properties.get(
                        county_column
                    )
                )
                if county_column
                else None
            )

            if not record:

                properties.update(
                    {
                        "sensd_spatial_assoc_x_value":
                            None,
                        "sensd_spatial_assoc_y_value":
                            None,
                        "sensd_spatial_assoc_standardized_x":
                            None,
                        "sensd_spatial_assoc_standardized_y":
                            None,
                        "sensd_spatial_assoc_lag_y":
                            None,
                        "sensd_spatial_assoc_local_i":
                            None,
                        "sensd_spatial_assoc_p":
                            None,
                        "sensd_spatial_assoc_quadrant":
                            None,
                        "sensd_spatial_assoc_cluster_code":
                            "NO_DATA",
                        "sensd_spatial_assoc_cluster_label":
                            "No Data",
                        "sensd_spatial_assoc_interpretation":
                            "No Data",
                        "sensd_spatial_assoc_description":
                            "Feature excluded from analysis.",
                        "sensd_spatial_assoc_significant":
                            False,
                        "sensd_spatial_assoc_neighbor_count":
                            None,
                        "sensd_spatial_assoc_island":
                            False,
                    }
                )

                continue

            properties.update(
                {
                    "sensd_spatial_assoc_x_value":
                        record.get(
                            "x_value"
                        ),

                    "sensd_spatial_assoc_y_value":
                        record.get(
                            "y_value"
                        ),

                    "sensd_spatial_assoc_standardized_x":
                        record.get(
                            "standardized_x"
                        ),

                    "sensd_spatial_assoc_standardized_y":
                        record.get(
                            "standardized_y"
                        ),

                    "sensd_spatial_assoc_lag_y":
                        record.get(
                            "spatial_lag_y"
                        ),

                    "sensd_spatial_assoc_local_i":
                        record.get(
                            "local_bivariate_moran_i"
                        ),

                    "sensd_spatial_assoc_p":
                        record.get(
                            "pseudo_p_value"
                        ),

                    "sensd_spatial_assoc_quadrant":
                        record.get(
                            "quadrant"
                        ),

                    "sensd_spatial_assoc_cluster_code":
                        record.get(
                            "cluster_code"
                        ),

                    "sensd_spatial_assoc_cluster_label":
                        record.get(
                            "cluster_label"
                        ),

                    "sensd_spatial_assoc_interpretation":
                        record.get(
                            "interpretation"
                        ),

                    "sensd_spatial_assoc_description":
                        record.get(
                            "description"
                        ),

                    "sensd_spatial_assoc_significant":
                        bool(
                            record.get(
                                "significant",
                                False,
                            )
                        ),

                    "sensd_spatial_assoc_neighbor_count":
                        record.get(
                            "neighbor_count"
                        ),

                    "sensd_spatial_assoc_island":
                        bool(
                            record.get(
                                "is_island",
                                False,
                            )
                        ),
                }
            )

        dataset = (
            save_geojson_dataset(
                owner=request.user,
                geojson_data=
                    geojson_data,
                dataset_name=
                    uploaded_file.name,
                original_filename=
                    uploaded_file.name,
                file_type=
                    "GeoJSON",
            )
        )

        analysis_run = (
            save_analysis_run(
                dataset=
                    dataset,
                analysis_type=
                    "spatial_association",
                parameters={
                    "analysis_name":
                        "Spatial Association Analysis",
                    "method":
                        "Global and Local Bivariate Moran's I",
                    "geography_column":
                        geography_column,
                    "state_column":
                        state_column or None,
                    "county_column":
                        county_column or None,
                    "x_column":
                        x_column,
                    "y_column":
                        y_column,
                    "spatial_weights":
                        "Queen contiguity",
                    "weight_transformation":
                        "Row-standardized",
                    "analysis_direction":
                        f"{x_column} -> spatial lag of {y_column}",
                },
                summary=
                    summary,
            )
        )

        return JsonResponse(
            {
                "success": True,
                "filename":
                    uploaded_file.name,
                "dataset_id":
                    dataset.id,
                "analysis_run_id":
                    analysis_run.id,
                "x_column":
                    x_column,
                "y_column":
                    y_column,
                "summary":
                    make_json_safe(
                        summary
                    ),
                "records":
                    make_json_safe(
                        records
                    ),
                "geojson":
                    make_json_safe(
                        analyzed_geojson
                    ),
            }
        )

    except ValueError as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )

    except Exception as exc:

        print(
            "spatial_association_api error:",
            exc,
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )


# ============================================================
# SPATIAL REGRESSION ANALYSIS
# ============================================================

@require_http_methods(["POST"])
def spatial_regression_api(request):

    try:

        uploaded_file = (
            request.FILES.get("file")
        )

        geography_column = (
            request.POST.get(
                "geography_column",
                "",
            ).strip()
        )

        state_column = (
            request.POST.get(
                "state_column",
                "",
            ).strip()
        )

        county_column = (
            request.POST.get(
                "county_column",
                "",
            ).strip()
        )

        dependent_column = (
            request.POST.get(
                "dependent_column",
                "",
            ).strip()
        )

        significance_raw = (
            request.POST.get(
                "significance_level",
                "",
            ).strip()
        )

        independent_columns = (
            request.POST.getlist(
                "independent_columns"
            )
        )

        independent_columns = [
            str(column).strip()
            for column
            in independent_columns
            if str(column).strip()
        ]

        if (
            len(independent_columns) == 1
            and independent_columns[0].startswith("[")
        ):

            try:

                parsed_columns = json.loads(
                    independent_columns[0]
                )

                if isinstance(
                    parsed_columns,
                    list,
                ):

                    independent_columns = [
                        str(column).strip()
                        for column
                        in parsed_columns
                        if str(column).strip()
                    ]

            except json.JSONDecodeError:

                raise ValueError(
                    "Independent variables are not formatted correctly."
                )

        if not independent_columns:

            raw_columns = (
                request.POST.get(
                    "independent_columns_json",
                    "",
                ).strip()
            )

            if raw_columns:

                try:

                    parsed_columns = (
                        json.loads(
                            raw_columns
                        )
                    )

                except json.JSONDecodeError as exc:

                    raise ValueError(
                        "Independent variables are not "
                        "formatted correctly."
                    ) from exc

                if not isinstance(
                    parsed_columns,
                    list,
                ):

                    raise ValueError(
                        "Independent variables must be "
                        "provided as a list."
                    )

                independent_columns = [
                    str(column).strip()
                    for column
                    in parsed_columns
                    if str(column).strip()
                ]

        if not uploaded_file:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "No analysis file received.",
                },
                status=400,
            )

        if not geography_column:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Geography Field is required.",
                },
                status=400,
            )

        if not dependent_column:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Dependent Variable is required.",
                },
                status=400,
            )

        if not independent_columns:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Select at least one independent variable.",
                },
                status=400,
            )

        if (
            dependent_column
            in independent_columns
        ):

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "The dependent variable cannot also "
                        "be an independent variable.",
                },
                status=400,
            )

        if (
            len(set(
                independent_columns
            ))
            != len(
                independent_columns
            )
        ):

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Independent variables must be unique.",
                },
                status=400,
            )

        geojson_data = (
            read_uploaded_geojson(
                uploaded_file
            )
        )

        validate_polygon_geojson(
            geojson_data
        )

        fields = (
            get_geojson_fields(
                geojson_data
            )
        )

        required_fields = [
            geography_column,
            dependent_column,
            *independent_columns,
        ]

        if state_column:
            required_fields.append(
                state_column
            )

        if county_column:
            required_fields.append(
                county_column
            )

        missing_fields = [
            column
            for column
            in required_fields
            if column not in fields
        ]

        if missing_fields:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Selected fields are missing: "
                        + ", ".join(
                            missing_fields
                        ),
                },
                status=400,
            )

        analysis_kwargs = {

            "geojson_data":
                geojson_data,

            "geography_column":
                geography_column,

            "dependent_column":
                dependent_column,

            "independent_columns":
                independent_columns,
        }

        if significance_raw:

            try:

                analysis_kwargs[
                    "significance_level"
                ] = float(
                    significance_raw
                )

            except ValueError as exc:

                raise ValueError(
                    "Significance level must be numeric."
                ) from exc

        analysis = (
            calculate_spatial_regression(
                **analysis_kwargs
            )
        )

        summary = (
            analysis.get("summary")
            or {}
        )

        coefficients = (
            analysis.get(
                "coefficients"
            )
            or []
        )

        records = (
            analysis.get("records")
            or []
        )

        lookup = {
            geography_lookup_key(
                record.get("geography")
            ):
                record
            for record
            in records
        }

        analyzed_geojson = (
            json.loads(
                json.dumps(
                    geojson_data
                )
            )
        )

        for feature in (
            analyzed_geojson.get(
                "features"
            )
            or []
        ):

            properties = (
                feature.setdefault(
                    "properties",
                    {},
                )
            )

            lookup_key = (
                geography_lookup_key(
                    properties.get(
                        geography_column
                    )
                )
            )

            record = (
                lookup.get(
                    lookup_key
                )
            )

            properties[
                "sensd_state_name"
            ] = (
                make_json_safe(
                    properties.get(
                        state_column
                    )
                )
                if state_column
                else None
            )

            properties[
                "sensd_county_name"
            ] = (
                make_json_safe(
                    properties.get(
                        county_column
                    )
                )
                if county_column
                else None
            )

            if not record:

                properties.update(
                    {
                        "sensd_regression_observed":
                            None,

                        "sensd_regression_predicted":
                            None,

                        "sensd_regression_residual":
                            None,

                        "sensd_regression_standardized_residual":
                            None,

                        "sensd_regression_neighbor_count":
                            None,

                        "sensd_regression_island":
                            False,

                        "sensd_regression_included":
                            False,
                    }
                )

                continue

            properties.update(
                {
                    "sensd_regression_observed":
                        record.get(
                            "observed_value"
                        ),

                    "sensd_regression_predicted":
                        record.get(
                            "predicted_value"
                        ),

                    "sensd_regression_residual":
                        record.get(
                            "residual"
                        ),

                    "sensd_regression_standardized_residual":
                        record.get(
                            "standardized_residual"
                        ),

                    "sensd_regression_neighbor_count":
                        record.get(
                            "neighbor_count"
                        ),

                    "sensd_regression_island":
                        bool(
                            record.get(
                                "is_island",
                                False,
                            )
                        ),

                    "sensd_regression_included":
                        True,
                }
            )

        dataset = (
            save_geojson_dataset(
                owner=request.user,
                geojson_data=
                    geojson_data,

                dataset_name=
                    uploaded_file.name,

                original_filename=
                    uploaded_file.name,

                file_type=
                    "GeoJSON",
            )
        )

        analysis_run = (
            save_analysis_run(
                dataset=
                    dataset,

                analysis_type=
                    "spatial_regression",

                parameters={

                    "analysis_name":
                        "Spatial Regression Analysis",

                    "method":
                        "OLS Regression with Spatial Diagnostics",

                    "geography_column":
                        geography_column,

                    "state_column":
                        state_column or None,

                    "county_column":
                        county_column or None,

                    "dependent_column":
                        dependent_column,

                    "independent_columns":
                        independent_columns,

                    "spatial_weights":
                        "Queen contiguity",

                    "rook":
                        False,

                    "weight_transformation":
                        "Row-standardized",

                    "significance_level":
                        summary.get(
                            "significance_level"
                        ),

                    "diagnostics": [
                        "Residual Moran's I",
                        "LM Error",
                        "Robust LM Error",
                        "LM Lag",
                        "Robust LM Lag",
                    ],
                },

                summary={
                    **summary,

                    "coefficients":
                        coefficients,
                },
            )
        )

        return JsonResponse(
            {
                "success": True,

                "filename":
                    uploaded_file.name,

                "dataset_id":
                    dataset.id,

                "analysis_run_id":
                    analysis_run.id,

                "analysis_name":
                    "Spatial Regression Analysis",

                "method":
                    "OLS Regression with Spatial Diagnostics",

                "dependent_column":
                    dependent_column,

                "independent_columns":
                    independent_columns,

                "summary":
                    make_json_safe(
                        summary
                    ),

                "coefficients":
                    make_json_safe(
                        coefficients
                    ),

                "records":
                    make_json_safe(
                        records
                    ),

                "geojson":
                    make_json_safe(
                        analyzed_geojson
                    ),
            }
        )

    except ValueError as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )

    except Exception as exc:

        print(
            "spatial_regression_api error:",
            exc,
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )


# ============================================================
# COUNTY SALMONELLA RISK
# ============================================================

@require_http_methods(["POST"])
def county_salmonella_risk_api(request):

    try:

        payload = json.loads(
            request.body.decode(
                "utf-8"
            )
            or "{}"
        )

        cases = (
            payload.get("cases")
        )

        population = (
            payload.get("population")
        )

        if (
            cases is None
            or population is None
        ):

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Cases and population are required.",
                },
                status=400,
            )

        cases = float(
            cases
        )

        population = float(
            population
        )

        if not math.isfinite(
            cases
        ):

            raise ValueError(
                "Cases must be numeric."
            )

        if not math.isfinite(
            population
        ):

            raise ValueError(
                "Population must be numeric."
            )

        if cases < 0:

            raise ValueError(
                "Cases cannot be negative."
            )

        if population <= 0:

            raise ValueError(
                "Population must be greater than zero."
            )

        rate_per_100k = (
            cases
            / population
            * 100000.0
        )

        return JsonResponse(
            {
                "success": True,
                "result": {
                    "cases":
                        cases,
                    "population":
                        population,
                    "rate_per_100k":
                        rate_per_100k,
                },
            }
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )

    except Exception as exc:

        print(
            "county_salmonella_risk_api error:",
            exc,
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )


# ============================================================
# GEOGRAPHY VALUES
# ============================================================

@require_http_methods(["POST"])
def analysis_geography_values_api(request):

    try:

        uploaded_file = (
            request.FILES.get("file")
        )

        geography_column = (
            request.POST.get(
                "geography_column",
                "",
            ).strip()
        )

        if not uploaded_file:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "No file received.",
                },
                status=400,
            )

        if not geography_column:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Geography field is required.",
                },
                status=400,
            )

        extension = (
            get_file_extension(
                uploaded_file.name
            )
        )

        values = []

        if extension in (
            "geojson",
            "json",
        ):

            geojson_data = (
                read_uploaded_geojson(
                    uploaded_file
                )
            )

            fields = (
                get_geojson_fields(
                    geojson_data
                )
            )

            if geography_column not in fields:

                return JsonResponse(
                    {
                        "success": False,
                        "error":
                            f"Field '{geography_column}' "
                            "was not found.",
                    },
                    status=400,
                )

            seen = set()

            for feature in (
                geojson_data.get(
                    "features"
                )
                or []
            ):

                properties = (
                    feature.get(
                        "properties"
                    )
                    or {}
                )

                value = (
                    clean_geography_value(
                        properties.get(
                            geography_column
                        )
                    )
                )

                if (
                    value
                    and value not in seen
                ):

                    seen.add(
                        value
                    )

                    values.append(
                        value
                    )

        elif extension in (
            "csv",
            "xlsx",
            "xls",
        ):

            dataframe = (
                read_uploaded_dataframe(
                    uploaded_file
                )
            )

            if (
                geography_column
                not in dataframe.columns
            ):

                return JsonResponse(
                    {
                        "success": False,
                        "error":
                            f"Field '{geography_column}' "
                            "was not found.",
                    },
                    status=400,
                )

            values = [
                clean_geography_value(
                    value
                )
                for value
                in dataframe[
                    geography_column
                ].dropna()
            ]

            values = list(
                dict.fromkeys(
                    value
                    for value in values
                    if value
                )
            )

        else:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Unsupported file format.",
                },
                status=415,
            )

        return JsonResponse(
            {
                "success": True,
                "geography_column":
                    geography_column,
                "count":
                    len(values),
                "values":
                    make_json_safe(
                        values
                    ),
            }
        )

    except Exception as exc:

        print(
            "analysis_geography_values_api error:",
            exc,
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )


# ============================================================
# END OF FILE
# ============================================================
