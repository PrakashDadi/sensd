import os
import json
from django.conf import settings
from django.contrib.gis.geos import Point
from mapsapp.models import WalmartStore, SchnucksStore, SaveALotStore, WholeFoodsStore

GEOJSON_LOADERS = {
    'walmart': WalmartStore,
    'schnucks': SchnucksStore,
    'save_a_lot': SaveALotStore,
    'whole_foods': WholeFoodsStore,
}


def run():

    base_path = os.path.join(settings.BASE_DIR, 'mapsapp',
                             'static', 'mapsapp', 'geojson')
    for filename in os.listdir(base_path):
        if filename.endswith('.geojson'):
            file_path = os.path.join(base_path, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Determine the store type from the filename
            store_type = filename.split('.')[0].lower()
            if store_type in GEOJSON_LOADERS:
                # loader.objects.all().delete()  # Clear existing data
                loader = GEOJSON_LOADERS[store_type]
                count = 0

                for feature in data['features']:
                    properties = feature['properties']
                    geometry = feature['geometry']
                    if geometry['type'] != 'Point':
                        print(f"Skipping non-point geometry in {filename}")
                        continue
                    lon, lat = geometry['coordinates']

                    # Create a new store instance
                    loader.objects.update_or_create(
                        object_id=properties.get('OBJECTID', 0),
                        defaults={
                            'company': properties.get('Company', store_type.capitalize()),
                            'street': properties.get('Street', ''),
                            'city': properties.get('City', ''),
                            'state': properties.get('State', ''),
                            'zip_code': properties.get('Zip', ''),
                            'phone': properties.get('Phone', ''),
                            'latitude': lat,
                            'longitude': lon,
                            # Assuming WGS84
                            'location': Point(lon, lat, srid=4326)
                        }
                    )
                    count += 1
                print(
                    f"Loader or updated {count} records for {store_type.capitalize()} from {filename}")
