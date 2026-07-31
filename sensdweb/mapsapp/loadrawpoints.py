import json
import os
from django.conf import settings
from django.contrib.gis.geos import Point
from geosens.models import RawPoint


def run():
    file_path = os.path.join(settings.BASE_DIR, 'geosens',
                             'static', 'geojson', 'Raw_Points.geojson')

    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    count = 0
    for feature in data['features']:
        props = feature['properties']
        coords = feature['geometry']['coordinates']  # [lng, lat]

        lon = coords[0]
        lat = coords[1]

        node_full = props.get('Node', '')              # "Farm1", "Market2"
        node_type = node_full.rstrip('0123456789')     # "Farm", "Market"

        RawPoint.objects.update_or_create(
            object_id=str(props['OBJECTID']),
            defaults={
                'node_name':    node_full,
                'node_type':    node_type,
                'product_type': props.get('Product_Type', ''),
                'latitude':     lat,
                'longitude':    lon,
                'location':     Point(lon, lat, srid=4326),
            }
        )
        count += 1

    print(f"Loaded or updated {count} raw point records.")