"""Build owner-scoped map data from saved Intelligent Distribution results."""

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings


CATALOG_PATH = (
    Path(settings.BASE_DIR)
    / "mapsapp"
    / "static"
    / "mapsapp"
    / "geojson"
    / "Flow_with_quantity.geojson"
)


def _text(value):
    return "" if value is None else str(value).strip()


def _node(properties, prefix):
    latitude = properties.get(f"{prefix}_Latitude")
    longitude = properties.get(f"{prefix}_Longitude")
    if latitude is None or longitude is None:
        return None
    return {
        "id": _text(properties.get(f"{prefix}_ID")),
        "name": _text(properties.get(f"{prefix}_Node")),
        "city_area": _text(properties.get(f"{prefix}_City_Area")),
        "state": _text(properties.get(f"{prefix}_State")),
        "latitude": float(latitude),
        "longitude": float(longitude),
    }


@lru_cache(maxsize=1)
def node_catalog():
    """Return immutable Midwest node metadata keyed by workbook node ID."""
    with CATALOG_PATH.open("r", encoding="utf-8") as source:
        data = json.load(source)

    catalog = {}
    for feature in data.get("features", []):
        properties = feature.get("properties") or {}
        for prefix in ("From", "To"):
            node = _node(properties, prefix)
            if node and node["id"]:
                catalog.setdefault(node["id"], node)
    return catalog


def request_flow_geojson(record):
    """Join saved request quantities to the reference node-location catalog."""
    catalog = node_catalog()
    features = []
    missing_nodes = set()
    total_flows = 0

    for flow in record.x_vars.all().order_by("pk"):
        total_flows += 1
        from_id, to_id = _text(flow.node_i), _text(flow.node_j)
        from_node, to_node = catalog.get(from_id), catalog.get(to_id)
        if not from_node or not to_node:
            if not from_node:
                missing_nodes.add(from_id)
            if not to_node:
                missing_nodes.add(to_id)
            continue

        features.append({
            "type": "Feature",
            "id": flow.pk,
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [from_node["longitude"], from_node["latitude"]],
                    [to_node["longitude"], to_node["latitude"]],
                ],
            },
            "properties": {
                "product_type_i": _text(flow.product),
                "product_type_j": _text(flow.product_div),
                "from_id": from_id,
                "from_node": from_node["name"],
                "from_city_area": from_node["city_area"],
                "from_state": from_node["state"],
                "from_latitude": from_node["latitude"],
                "from_longitude": from_node["longitude"],
                "to_id": to_id,
                "to_node": to_node["name"],
                "to_city_area": to_node["city_area"],
                "to_state": to_node["state"],
                "to_latitude": to_node["latitude"],
                "to_longitude": to_node["longitude"],
                "mode": _text(flow.mode),
                "quantity": float(flow.quantity),
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "request_id": record.pk,
            "total_flows": total_flows,
            "mapped_flows": len(features),
            "unmapped_flows": total_flows - len(features),
            "missing_node_ids": sorted(node for node in missing_nodes if node),
        },
    }
