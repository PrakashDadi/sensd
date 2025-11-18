import json
import os
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from mapsapp.models import CountyBivariate


def run():
    file_path = os.path.join(
        settings.BASE_DIR, "mapsapp", "static", "mapsapp", "geojson", "bivariatemap.geojson"
    )

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    # Clear existing data before reload to avoid duplicates
    CountyBivariate.objects.all().delete()  # pylint: disable=no-member

    count = 0
    for feature in data["features"]:
        props = feature["properties"]
        geom = GEOSGeometry(json.dumps(feature["geometry"])) if feature.get(
            "geometry") else None

        # Ensure all geometries are MultiPolygons
        if geom and isinstance(geom, Polygon):
            geom = MultiPolygon(geom)

        CountyBivariate.objects.create(  # pylint: disable=no-member
            geoid=props.get("GEOID"),
            geo_id=props.get("GEO_ID"),
            state=props.get("STATE"),
            county=props.get("COUNTY"),
            name=props.get("NAME"),
            lsad=props.get("LSAD"),
            state_name=props.get("StateName"),
            stusps=props.get("STUSPS"),
            county_name=props.get("County_Name"),
            censusarea=props.get("CENSUSAREA"),
            objectid=props.get("OBJECTID"),
            statefp=props.get("STATEFP"),
            countyfp=props.get("COUNTYFP"),
            countyns=props.get("COUNTYNS"),
            intptlat=props.get("INTPTLAT"),
            intptlon=props.get("INTPTLON"),
            salmonella_rate=props.get("SalomellaRate_Rate_2022"),
            social_vulnerability=props.get(
                "SocialVulnerability_RPL_THEMES_2022"),
            salmonella_class=props.get("SalmonbellaClass"),
            svi_class=props.get("SVICLass"),
            bivariate_class=props.get("BivariateClass"),
            overall_food_insecurity=props.get("Overall_Food_Insecurity"),
            child_food_insecurity=props.get("Child_Food_Insecurity_Rate"),
            rpl_themes=props.get("RPL_Themes"),

            geom=geom,
        )
        count += 1

    print(f"Reloaded {count} CountyBivariate records")
