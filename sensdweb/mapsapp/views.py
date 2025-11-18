from email.mime import base
import os
import json
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.http import HttpResponse
from mapsapp.models import Store, FSISCoordinates, CountyBivariate, USStates  # pylint: disable=no-member
from django.core.serializers import serialize

# Create your views here.


def home(request):
    return render(request, 'mapsapp/home.html')


def gis_dashboard(request):
    return render(request, 'mapsapp/index.html')


def geojson_from_queryset(queryset):
    features = []
    for obj in queryset:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [obj.longitude, obj.latitude]
            },
            "properties": {
                "company": obj.company,
                "street": obj.street,
                "city": obj.city,
                "state": obj.state,
                "zip": obj.zip_code,
                "phone": obj.phone
            }
        })
    return {
        "type": "FeatureCollection",
        "features": features
    }

def _company_match(name: str, variants: list[str]) -> bool:
     if not name:
         return False
     u = name.upper()
     return any(v in u for v in variants)

def _valid_coords(qs):
     return (qs.exclude(latitude__isnull=True, longitude__isnull=True)
               .exclude(latitude=0).exclude(longitude=0))


def walmart_geojson(request):
    base = _valid_coords(Store.objects.all())
    rows = [s for s in base if _company_match(s.company, ["WALMART","WAL-MART","WAL MART","SUPERCENTER"])]
    print("Walmart rows (py-filtered):", len(rows))
    return JsonResponse(geojson_from_queryset(rows))  # pylint: disable=no-member


def schnucks_geojson(request):
    base = _valid_coords(Store.objects.all())
    rows = [s for s in base if _company_match(s.company, ["SCHNUCKS"])]
    print("Schnucks rows (py-filtered):", len(rows))
    return JsonResponse(geojson_from_queryset(rows))  # pylint: disable=no-member


def save_a_lot_geojson(request):
    base = _valid_coords(Store.objects.all())
    rows = [s for s in base if _company_match(s.company, ["SAVE A LOT","SAVE-A-LOT","SAVEALOT"])]
    print("Schnucks rows (py-filtered):", len(rows))
    return JsonResponse(geojson_from_queryset(rows))# pylint: disable=no-member


def whole_foods_geojson(request):
    base = _valid_coords(Store.objects.all())
    rows = [s for s in base if _company_match(s.company, ["WHOLE FOODS","WHOLE FOODS MARKET"])]
    print("Schnucks rows (py-filtered):", len(rows))
    return JsonResponse(geojson_from_queryset(rows))  # pylint: disable=no-member

def fsis_coordinates_geojson(request):
    features = []
    for obj in FSISCoordinates.objects.all():  # pylint: disable=no-member
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [obj.longitude, obj.latitude]
            },
            "properties": {
                "company": obj.company,
                "est_number": obj.est_number,
                "city": obj.city,
                "state": obj.state,
                "zip": obj.zip_code,
                "phone": obj.phone or '',
                "activities": obj.activities or ''
            }
        })
    return JsonResponse({
        "type": "FeatureCollection",
        "features": features
    })


def county_bivariate_geojson(request):
    qs = CountyBivariate.objects.all()  # pylint: disable=no-member

    geojson = serialize(
        "geojson",
        qs,
        geometry_field="geom",
        fields=(
            "geoid",
            "state_name", "county_name",
            "salmonella_rate", "social_vulnerability",
            "salmonella_class", "svi_class",
            "bivariate_class", "child_food_insecurity",
        ),
    )
    return HttpResponse(geojson, content_type="application/json")


def us_states_geojson(request):
    """
    Returns GeoJSON for all US States — outlines only, no popups.
    """
    geojson_data = serialize(
        'geojson',
        USStates.objects.all(),  # pylint: disable=no-member
        geometry_field='geom',
        fields=('state_name', 'state_fips'),
    )
    return HttpResponse(geojson_data, content_type='application/json')