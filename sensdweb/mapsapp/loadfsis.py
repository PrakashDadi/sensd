import json
import os
from django.conf import settings
from django.contrib.gis.geos import Point
from mapsapp.models import FSISCoordinates


def run():
    file_path = os.path.join(
        settings.BASE_DIR,
        'mapsapp', 'static', 'mapsapp', 'geojson',
        'Bivariate FSIS.geojson'
    )

    if not os.path.exists(file_path):
        print(f"FSIS GeoJSON file not found at: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    count = 0
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        lat = props.get("Latitude")
        lon = props.get("Longitude")
        object_id = props.get("OBJECTID")
        est_id = props.get("Establishment_ID")

        if lat is None or lon is None or object_id is None:
            continue  # skip incomplete features

        FSISCoordinates.objects.update_or_create(  # pylint: disable=no-member
            object_id=object_id,
            defaults={
                "company": props.get("Company", ""),
                "est_number": props.get("EstNumber", ""),
                "establishment_id": est_id or "",
                "street": props.get("Street", ""),
                "city": props.get("City", ""),
                "state": props.get("State", ""),
                "zip_code": str(props.get("Zip", "")),
                "phone": props.get("Phone", ""),
                "activities": props.get("Activities", "") or "",
                "dbas": props.get("DBAs", "") or "",
                "county": props.get("County", ""),
                "latitude": lat,
                "longitude": lon,
                "location": Point(lon, lat, srid=4326)
            }
        )
        count += 1

    print(f"Successfully loaded or updated {count} FSIS records.")
