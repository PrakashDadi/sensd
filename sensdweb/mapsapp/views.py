import json

import pandas as pd
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from mapsapp.models import (
    CountyBivariate,
    FSISCoordinates,
    FlowLineQuantity,
    FlowWithQuantity,
    Store,
    USStates,
    UploadedLayer,
)


def home(request):
    return render(request, "gisdashboards/gishome.html")


def gis_dashboard(request):
    return render(request, "gisdashboards/gisindex.html")


def maps_view(request):
    return render(request, "gisdashboards/gismaps.html")


def grid_view(request):
    return render(request, "gisdashboards/grid_view.html")


def data_mapping_tool_view(request):
    return render(request, "gisdashboards/gisdata_mapping_tool.html")


def flow_analysis_view(request):
    return render(request, "gisdashboards/gisflow_analysis.html")


def val(obj, field):
    """Safely read encrypted or plain fields for JSON output."""
    try:
        value = getattr(obj, field)
        return value if value is not None else ""
    except Exception:
        return ""


def geojson_feature(obj, geom_field, prop_fields):
    geom = getattr(obj, geom_field)
    geometry = json.loads(geom.geojson) if geom else None
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {field: val(obj, field) for field in prop_fields},
    }


def filter_stores(keyword):
    results = []
    for store in Store.objects.all():  # pylint: disable=no-member
        company = val(store, "company").lower()
        if keyword in company:
            results.append(store)
    return results


def walmart_geojson(request):
    qs = filter_stores("walmart")
    return JsonResponse(
        {
            "type": "FeatureCollection",
            "features": [
                geojson_feature(
                    store,
                    "location",
                    ["company", "street", "city", "state", "zip_code", "phone"],
                )
                for store in qs
            ],
        }
    )


def schnucks_geojson(request):
    qs = filter_stores("schnucks")
    return JsonResponse(
        {
            "type": "FeatureCollection",
            "features": [
                geojson_feature(
                    store,
                    "location",
                    ["company", "street", "city", "state", "zip_code", "phone"],
                )
                for store in qs
            ],
        }
    )


def save_a_lot_geojson(request):
    qs = filter_stores("save a lot")
    return JsonResponse(
        {
            "type": "FeatureCollection",
            "features": [
                geojson_feature(
                    store,
                    "location",
                    ["company", "street", "city", "state", "zip_code", "phone"],
                )
                for store in qs
            ],
        }
    )


def whole_foods_geojson(request):
    qs = filter_stores("whole foods")
    return JsonResponse(
        {
            "type": "FeatureCollection",
            "features": [
                geojson_feature(
                    store,
                    "location",
                    ["company", "street", "city", "state", "zip_code", "phone"],
                )
                for store in qs
            ],
        }
    )


def flow_with_quantity_geojson(request):
    qs = FlowWithQuantity.objects.all()  # pylint: disable=no-member
    return JsonResponse(
        {
            "type": "FeatureCollection",
            "features": [
                geojson_feature(
                    flow,
                    "location",
                    [
                        "object_id",
                        "from_id",
                        "from_node",
                        "from_city_area",
                        "from_state",
                        "from_latitude",
                        "from_longitude",
                        "to_id",
                        "to_node",
                        "to_city_area",
                        "to_state",
                        "to_latitude",
                        "to_longitude",
                        "product_type_i",
                        "product_type_j",
                        "quantity",
                    ],
                )
                for flow in qs
            ],
        }
    )


def flow_line_quantity_geojson(request):
    qs = FlowLineQuantity.objects.all()  # pylint: disable=no-member
    return JsonResponse(
        {
            "type": "FeatureCollection",
            "features": [
                geojson_feature(
                    flow,
                    "line",
                    [
                        "oid",
                        "from_id",
                        "from_node",
                        "from_city_area",
                        "from_state",
                        "to_id",
                        "to_node",
                        "to_city_area",
                        "to_state",
                        "product_type_i",
                        "product_type_j",
                        "quantity",
                    ],
                )
                for flow in qs
            ],
        }
    )


def fsis_coordinates_geojson(request):
    qs = FSISCoordinates.objects.all()  # pylint: disable=no-member
    return JsonResponse(
        {
            "type": "FeatureCollection",
            "features": [
                geojson_feature(
                    fsis,
                    "location",
                    ["company", "est_number", "city", "state", "zip_code", "activities"],
                )
                for fsis in qs
            ],
        }
    )


def county_bivariate_geojson(request):
    qs = CountyBivariate.objects.all()  # pylint: disable=no-member
    return JsonResponse(
        {
            "type": "FeatureCollection",
            "features": [
                geojson_feature(
                    county,
                    "geom",
                    [
                        "county_name",
                        "state_name",
                        "overall_food_insecurity",
                        "social_vulnerability",
                        "bivariate_class",
                    ],
                )
                for county in qs
            ],
        }
    )


def us_states_geojson(request):
    qs = USStates.objects.all()  # pylint: disable=no-member
    return JsonResponse(
        {
            "type": "FeatureCollection",
            "features": [
                geojson_feature(state, "geom", ["state_name"])
                for state in qs
            ],
        }
    )


UPLOADED_FLOW_REQUIRED_COLS = [
    "From_ID",
    "From_Latitude",
    "From_Longitude",
    "To_ID",
    "To_Latitude",
    "To_Longitude",
    "Quantity",
]


@csrf_exempt
@require_http_methods(["POST"])
def upload_flow_api(request):
    try:
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return JsonResponse(
                {"success": False, "error": "No file received."}, status=400
            )

        ext = uploaded_file.name.split(".")[-1].lower()
        features = []

        if ext in ["geojson", "json"]:
            data = json.loads(uploaded_file.read().decode("utf-8"))

            for feature in data.get("features", []):
                props = feature.get("properties", {})
                props_lower = {key.lower(): value for key, value in props.items()}

                def get_prop(key):
                    return props_lower.get(key.lower(), "")

                try:
                    from_lat = float(get_prop("from_latitude"))
                    from_lon = float(get_prop("from_longitude"))
                    to_lat = float(get_prop("to_latitude"))
                    to_lon = float(get_prop("to_longitude"))
                    qty = float(get_prop("quantity"))
                except (TypeError, ValueError):
                    continue

                features.append(
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [from_lon, from_lat],
                        },
                        "properties": {
                            "from_id": str(get_prop("from_id")),
                            "from_node": str(get_prop("from_node")),
                            "from_city_area": str(get_prop("from_city_area")),
                            "from_state": str(get_prop("from_state")),
                            "from_latitude": from_lat,
                            "from_longitude": from_lon,
                            "to_id": str(get_prop("to_id")),
                            "to_node": str(get_prop("to_node")),
                            "to_city_area": str(get_prop("to_city_area")),
                            "to_state": str(get_prop("to_state")),
                            "to_latitude": to_lat,
                            "to_longitude": to_lon,
                            "product_type_i": str(get_prop("product_type_i")).strip(),
                            "product_type_j": str(get_prop("product_type_j")).strip(),
                            "quantity": qty,
                        },
                    }
                )
        elif ext in ["csv", "xlsx", "xls"]:
            df = pd.read_csv(uploaded_file) if ext == "csv" else pd.read_excel(uploaded_file)
            missing = [col for col in UPLOADED_FLOW_REQUIRED_COLS if col not in df.columns]
            if missing:
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"Missing required columns: {', '.join(missing)}",
                    },
                    status=400,
                )

            for _, row in df.iterrows():
                try:
                    from_lat = float(row["From_Latitude"])
                    from_lon = float(row["From_Longitude"])
                    to_lat = float(row["To_Latitude"])
                    to_lon = float(row["To_Longitude"])
                    qty = float(row["Quantity"])
                except (TypeError, ValueError):
                    continue

                features.append(
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [from_lon, from_lat],
                        },
                        "properties": {
                            "from_id": str(row.get("From_ID", "")),
                            "from_node": str(row.get("From_Node", "")),
                            "from_city_area": str(row.get("From_City_Area", "")),
                            "from_state": str(row.get("From_State", "")),
                            "from_latitude": from_lat,
                            "from_longitude": from_lon,
                            "to_id": str(row.get("To_ID", "")),
                            "to_node": str(row.get("To_Node", "")),
                            "to_city_area": str(row.get("To_City_Area", "")),
                            "to_state": str(row.get("To_State", "")),
                            "to_latitude": to_lat,
                            "to_longitude": to_lon,
                            "product_type_i": str(row.get("Product_Type_i", "")).strip(),
                            "product_type_j": str(row.get("Product_Type_j", "")).strip(),
                            "quantity": qty,
                        },
                    }
                )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Only CSV, Excel, or GeoJSON supported.",
                },
                status=415,
            )

        if not features:
            return JsonResponse(
                {"success": False, "error": "No valid flow rows found in the file."},
                status=400,
            )

        return JsonResponse(
            {
                "success": True,
                "filename": uploaded_file.name,
                "rows_loaded": len(features),
                "geojson": {"type": "FeatureCollection", "features": features},
            }
        )
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def upload_data_api(request):
    try:
        uploaded_file = request.FILES.get("file")
        lat_col = request.POST.get("lat_column", "Latitude")
        lng_col = request.POST.get("lng_column", "Longitude")

        if not uploaded_file:
            return JsonResponse(
                {"success": False, "error": "No file received."}, status=400
            )

        file_extension = uploaded_file.name.split(".")[-1].lower()
        geojson_content = None
        feature_count = 0
        layer_type = ""

        if file_extension in ["csv", "xlsx", "xls"]:
            df = pd.read_csv(uploaded_file) if file_extension == "csv" else pd.read_excel(uploaded_file)

            if lat_col not in df.columns or lng_col not in df.columns:
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"Coordinates columns not found ({lat_col}, {lng_col}).",
                    },
                    status=400,
                )

            features = []
            for _, row in df.iterrows():
                try:
                    lat = float(row[lat_col])
                    lng = float(row[lng_col])
                except (TypeError, ValueError):
                    continue

                properties = row.drop([lat_col, lng_col]).to_dict()
                properties = {
                    key: value if pd.notna(value) else None
                    for key, value in properties.items()
                }
                features.append(
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [lng, lat],
                        },
                        "properties": properties,
                    }
                )

            feature_count = len(features)
            geojson_content = json.dumps(
                {"type": "FeatureCollection", "features": features}
            )
            layer_type = "Point"
        elif file_extension in ["geojson", "json"]:
            data = json.loads(uploaded_file.read().decode("utf-8"))
            layer_type = "Point"

            if data.get("type") == "FeatureCollection":
                repaired_features = []
                for feature in data.get("features", []):
                    props = feature.get("properties", {})
                    geometry = feature.get("geometry")

                    if geometry is None and "Latitude" in props and "Longitude" in props:
                        try:
                            lat = float(props["Latitude"])
                            lon = float(props["Longitude"])
                        except (TypeError, ValueError):
                            continue

                        feature["geometry"] = {
                            "type": "Point",
                            "coordinates": [lon, lat],
                        }
                        del props["Latitude"]
                        del props["Longitude"]
                        repaired_features.append(feature)
                    elif geometry is not None:
                        repaired_features.append(feature)

                data["features"] = repaired_features
                feature_count = len(repaired_features)
                if feature_count and repaired_features[0].get("geometry"):
                    layer_type = repaired_features[0]["geometry"].get("type", "Unknown")

            geojson_content = json.dumps(data)
        else:
            return JsonResponse(
                {"success": False, "error": "Unsupported file format."}, status=415
            )

        layer = UploadedLayer.objects.create(  # pylint: disable=no-member
            name=uploaded_file.name,
            file_type=file_extension.upper(),
            feature_count=feature_count,
            layer_type=layer_type,
            geojson_data=geojson_content,
        )

        return JsonResponse(
            {
                "success": True,
                "layer_id": layer.id,
                "features_created": feature_count,
            }
        )
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


@require_http_methods(["GET"])
def list_user_layers_api(request):
    layers_queryset = UploadedLayer.objects.all().order_by("-id")  # pylint: disable=no-member
    layers_list = [
        {
            "id": layer.id,
            "name": layer.name,
            "file_type": layer.file_type,
            "feature_count": layer.feature_count,
            "type": layer.layer_type,
        }
        for layer in layers_queryset
    ]
    return JsonResponse({"layers": layers_list})


@require_http_methods(["GET"])
def get_layer_geojson_api(request, layer_id):
    layer = get_object_or_404(UploadedLayer, id=layer_id)
    try:
        return JsonResponse(json.loads(layer.geojson_data))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid GeoJSON data stored."}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_layer_api(request, layer_id):
    layer = get_object_or_404(UploadedLayer, id=layer_id)
    layer.delete()
    return JsonResponse({"success": True})
