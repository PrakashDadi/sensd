# mapsapp/load_metrics.py
import json
import os
from django.conf import settings
from mapsapp.models import CountyMetric


def run():
    file_path = os.path.join(settings.BASE_DIR, 'mapsapp',
                             'static', 'mapsapp', 'geojson', 'county_metrics_sample.json')

    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    count = 0
    for item in data:
        CountyMetric.objects.update_or_create(  # pylint: disable=no-member
            fips=item["fips"],
            defaults={
                "county": item["county"],
                "state": item["state"],
                "salmonella_rate": item["salmonella_rate"],
                "svi_score": item["svi_score"],
                "food_insecurity": item["food_insecurity"]
            }
        )
        count += 1

    print(f"Loaded or updated {count} CountyMetric records.")
