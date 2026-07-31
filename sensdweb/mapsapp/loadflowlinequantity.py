import json
import os
from django.conf import settings
from django.contrib.gis.geos import LineString
from geosens.models import FlowLineQuantity


def run():
    file_path = os.path.join(settings.BASE_DIR, 'geosens',
                             'static', 'geojson', 'Flow_line_quantity.geojson')

    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    count = 0
    for feature in data['features']:
        props = feature['properties']
        coords = feature['geometry']['coordinates']  # [[lng, lat], ...]

        FlowLineQuantity.objects.update_or_create(
            oid=props['OID'],
            defaults={
                'product_type_i': props.get('Product_Type_i', '').strip(),
                'from_id':        props.get('From_ID', ''),
                'from_node':      props.get('From_Node', ''),
                'from_city_area': props.get('From_City_Area', ''),
                'from_state':     props.get('From_State', ''),
                'from_latitude':  props.get('From_Latitude'),
                'from_longitude': props.get('From_Longitude'),
                'product_type_j': props.get('Product_Type_j', '').strip(),
                'to_id':          props.get('To_ID', ''),
                'to_node':        props.get('To_Node', ''),
                'to_city_area':   props.get('To_City_Area', ''),
                'to_state':       props.get('To_State', ''),
                'to_latitude':    props.get('To_Latitude'),
                'to_longitude':   props.get('To_Longitude'),
                'quantity':       props.get('Quantity'),
                'orig_fid':       props.get('ORIG_FID'),
                'shape_length':   props.get('Shape_Length'),
                'line':           LineString(coords, srid=4326),
            }
        )
        count += 1

    print(f"Loaded or updated {count} flow line records.")