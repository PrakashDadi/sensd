import json
import os
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from mapsapp.models import USStates


def run():
    file_path = os.path.join(
        settings.BASE_DIR, "mapsapp", "static", "mapsapp", "geojson", "states.geojson"
    )

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    # Clear existing records to avoid duplicates
    USStates.objects.all().delete()  # pylint: disable=no-member

    count = 0
    for feature in data["features"]:
        props = feature["properties"]
        geom = GEOSGeometry(json.dumps(feature["geometry"])) if feature.get(
            "geometry") else None

        # Ensure geometry is a MultiPolygon
        if geom and isinstance(geom, Polygon):
            geom = MultiPolygon(geom)

        USStates.objects.create(  # pylint: disable=no-member
            state_name=props.get("NAME"),
            state_fips=props.get("STATEFP"),
            geom=geom,
        )
        count += 1

    print(f"Reloaded {count} USStateBoundary records successfully.")
