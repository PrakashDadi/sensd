import json
import os
from django.conf import settings
from django.contrib.gis.geos import LineString
from geosens.models import RawPointFlow


def run():
    file_path = os.path.join(settings.BASE_DIR, 'geosens',
                             'static', 'geojson', 'Raw_Points_Flow.geojson')

    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    count = 0
    for feature in data['features']:
        props = feature['properties']
        coords = feature['geometry']['coordinates']  # list of [lng, lat] pairs

        RawPointFlow.objects.update_or_create(
            oid=props['OID'],
            defaults={
                'from_id':        props.get('From_ID', ''),
                'from_latitude':  props.get('From_Latitude'),
                'from_longitude': props.get('From_Longitude'),
                'to_id':          props.get('To_ID', ''),
                'to_latitude':    props.get('To_Latitude'),
                'to_longitude':   props.get('To_Longitude'),
                'product_type_i': props.get('Product_Type_i', ''),
                'product_type_j': props.get('Product_Type_j', ''),
                'quantity':       props.get('Quantity'),
                'orig_fid':       props.get('ORIG_FID'),
                'shape_length':   props.get('Shape_Length'),
                'line':           LineString(coords, srid=4326),
            }
        )
        count += 1

    print(f"Loaded or updated {count} raw point flow records.")