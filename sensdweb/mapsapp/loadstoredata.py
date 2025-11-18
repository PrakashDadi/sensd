import json
import os
from django.conf import settings
from django.contrib.gis.geos import Point
from mapsapp.models import Store


def run():
    file_path = os.path.join(settings.BASE_DIR, 'mapsapp',
                             'static', 'mapsapp', 'geojson', 'allstores.geojson')

    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    count = 0
    for feature in data['features']:
        props = feature['properties']

        # Extract coordinates directly from properties
        lon = float(props['Longitude'])
        lat = float(props['Latitude'])

        Store.objects.update_or_create(  # pylint: disable=no-member
            object_id=f"{props['Retailor Name'][:3].upper()}_{props['ObjectID']}",
            defaults={
                'company': props['Retailor Name'],
                'street': props['Street'],
                'city': props['City'],
                'state': props['State'],
                'zip_code': str(props['Zip Code']),
                'phone': props['Phone'],
                'latitude': lat,
                'longitude': lon,
                'location': Point(lon, lat, srid=4326)
            }
        )
        count += 1

    print(f"Loaded or updated {count} store records.")
