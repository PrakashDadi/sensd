import io
import json
import random

import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from authentication.models import CustomUser
from mapsapp.analysis.bivariate import calculate_bivariate_map
from mapsapp.analysis.local_moran import calculate_local_moran
from mapsapp.analysis.salmonella import calculate_salmonella_risk_map
from mapsapp.analysis.spatial_association import calculate_spatial_association
from mapsapp.analysis.spatial_regression import calculate_spatial_regression
from mapsapp.models import AnalysisRun, UploadedDataset, UploadedFeature


def randomized_spatial_data(seed=20260913, width=5, height=5):
    """Create deterministic random attributes on a contiguous polygon grid."""
    randomizer = random.Random(seed)
    rows = []
    features = []

    for y in range(height):
        for x in range(width):
            geoid = f"{y * width + x + 1:05d}"
            food = round(randomizer.uniform(0.05, 0.35), 4)
            properties = {
                "geoid": geoid,
                "state": "Test State",
                "county": f"County {geoid}",
                "cases": randomizer.randint(2, 80),
                "population": randomizer.randint(5_000, 50_000),
                "food": food,
                "svi": round(0.25 * food + randomizer.uniform(0.0, 0.25), 4),
            }
            rows.append(properties)
            features.append(
                {
                    "type": "Feature",
                    "properties": properties,
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [x, y],
                                [x + 1, y],
                                [x + 1, y + 1],
                                [x, y + 1],
                                [x, y],
                            ]
                        ],
                    },
                }
            )

    return pd.DataFrame(rows), {"type": "FeatureCollection", "features": features}


class SpatialAlgorithmTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dataframe, cls.geojson = randomized_spatial_data()

    def test_all_analysis_engines_accept_randomized_polygon_data(self):
        salmonella = calculate_salmonella_risk_map(
            self.dataframe,
            geography_column="geoid",
            cases_column="cases",
            population_column="population",
        )
        bivariate = calculate_bivariate_map(
            self.dataframe,
            geography_column="geoid",
            x_column="food",
            y_column="svi",
        )
        local_moran = calculate_local_moran(
            geojson_data=self.geojson,
            geography_column="geoid",
            value_column="food",
            permutations=19,
            significance_level=0.05,
            seed=7,
        )
        association = calculate_spatial_association(
            self.geojson,
            "geoid",
            "food",
            "svi",
            permutations=19,
            significance_level=0.05,
            seed=7,
        )
        regression = calculate_spatial_regression(
            self.geojson,
            "geoid",
            "cases",
            ["population", "food"],
            significance_level=0.05,
        )

        for result in (salmonella, bivariate, local_moran, association):
            self.assertEqual(len(result["records"]), 25)
            self.assertIn("summary", result)
        self.assertEqual(len(regression["records"]), 25)
        self.assertIn("coefficients", regression)


class SpatialApiTests(TestCase):
    def setUp(self):
        self.client.enforce_csrf_checks = True
        self.user = CustomUser.objects.create_user(
            username="spatial-tester",
            email="spatial@example.test",
            password="test-password-only",
        )
        self.client.force_login(self.user)
        self.dataframe, self.geojson = randomized_spatial_data()
        page_response = self.client.get(reverse("spatial_analysis"))
        self.csrf_token = page_response.cookies["csrftoken"].value

    def upload(self, filename, content, content_type, **fields):
        payload = {
            "file": SimpleUploadedFile(filename, content, content_type=content_type),
            "csrfmiddlewaretoken": self.csrf_token,
            **fields,
        }
        return payload

    def geojson_upload(self, filename="random-polygons.geojson", **fields):
        return self.upload(
            filename,
            json.dumps(self.geojson).encode("utf-8"),
            "application/geo+json",
            **fields,
        )

    def test_spatial_page_uses_sensd_navigation(self):
        response = self.client.get(reverse("spatial_analysis"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Spatial Analysis")
        self.assertContains(response, reverse("gis-home"))
        self.assertNotContains(response, "tile.openstreetmap.org")
        self.assertNotContains(response, "unpkg.com/leaflet")
        self.assertContains(response, "mapsapp/vendor/leaflet/leaflet.js")
        self.assertContains(response, "SENSD U.S. States")
        self.assertContains(response, reverse("us_states_geojson"))
        self.assertContains(response, "Blank (No Basemap)")

    def test_column_inspection_supports_csv_excel_and_geojson(self):
        csv_bytes = self.dataframe.to_csv(index=False).encode("utf-8")
        csv_response = self.client.post(
            reverse("spatial_inspect_columns_api"),
            self.upload("random.csv", csv_bytes, "text/csv"),
        )

        excel_buffer = io.BytesIO()
        self.dataframe.to_excel(excel_buffer, index=False)
        excel_response = self.client.post(
            reverse("spatial_inspect_columns_api"),
            self.upload(
                "random.xlsx",
                excel_buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        )

        geojson_response = self.client.post(
            reverse("spatial_inspect_columns_api"),
            self.geojson_upload(),
        )

        for response in (csv_response, excel_response, geojson_response):
            self.assertEqual(response.status_code, 200, response.content)
            self.assertTrue(response.json()["success"])
            self.assertIn("geoid", response.json()["columns"])

    def test_reference_and_flow_uploads_persist_for_authenticated_owner(self):
        reference_response = self.client.post(
            reverse("spatial_upload_reference_api"),
            self.geojson_upload(),
        )
        self.assertEqual(reference_response.status_code, 200, reference_response.content)

        flow = pd.DataFrame(
            [
                {
                    "from_id": "A",
                    "from_lat": 38.6,
                    "from_lng": -90.2,
                    "to_id": "B",
                    "to_lat": 39.1,
                    "to_lng": -89.8,
                    "quantity": 12.5,
                }
            ]
        )
        flow_response = self.client.post(
            reverse("spatial_upload_flow_api"),
            self.upload(
                "random-flow.csv",
                flow.to_csv(index=False).encode("utf-8"),
                "text/csv",
                from_id="from_id",
                from_latitude="from_lat",
                from_longitude="from_lng",
                to_id="to_id",
                to_latitude="to_lat",
                to_longitude="to_lng",
                quantity="quantity",
            ),
        )
        self.assertEqual(flow_response.status_code, 200, flow_response.content)
        self.assertEqual(UploadedDataset.objects.filter(owner=self.user).count(), 2)
        self.assertEqual(UploadedFeature.objects.count(), 26)

    def test_all_analysis_apis_persist_encrypted_results(self):
        endpoints = [
            (
                "spatial_salmonella_risk_map_api",
                {"geography_column": "geoid", "cases_column": "cases", "population_column": "population"},
            ),
            (
                "spatial_bivariate_map_api",
                {"geography_column": "geoid", "x_column": "food", "y_column": "svi"},
            ),
            (
                "spatial_local_moran_api",
                {"geography_column": "geoid", "value_column": "food", "permutations": "19", "seed": "7"},
            ),
            (
                "spatial_association_api",
                {"geography_column": "geoid", "x_column": "food", "y_column": "svi", "permutations": "19", "seed": "7"},
            ),
            (
                "spatial_regression_api",
                {
                    "geography_column": "geoid",
                    "dependent_column": "cases",
                    "independent_columns_json": json.dumps(["population", "food"]),
                },
            ),
        ]

        for endpoint, fields in endpoints:
            response = self.client.post(reverse(endpoint), self.geojson_upload(**fields))
            self.assertEqual(response.status_code, 200, response.content)
            self.assertTrue(response.json()["success"])

        self.assertEqual(UploadedDataset.objects.filter(owner=self.user).count(), 5)
        self.assertEqual(AnalysisRun.objects.count(), 5)

        dataset = UploadedDataset.objects.first()
        self.assertEqual(dataset.owner, self.user)
        self.assertEqual(dataset.name, "random-polygons.geojson")
        self.assertIn("geoid", json.loads(dataset.fields))

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name, fields FROM mapsapp_uploadeddataset WHERE id = %s",
                [dataset.pk],
            )
            stored_name, stored_fields = cursor.fetchone()

        self.assertNotEqual(stored_name, "random-polygons.geojson")
        self.assertNotIn("geoid", stored_fields)

    def test_anonymous_user_is_redirected_before_spatial_api_runs(self):
        self.client.logout()
        response = self.client.post(
            reverse("spatial_inspect_columns_api"),
            self.geojson_upload(),
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_supporting_county_and_geography_endpoints(self):
        county_response = self.client.post(
            reverse("spatial_county_salmonella_risk_api"),
            data=json.dumps({"cases": 25, "population": 100_000}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )
        self.assertEqual(county_response.status_code, 200, county_response.content)
        self.assertEqual(county_response.json()["result"]["rate_per_100k"], 25.0)

        geography_response = self.client.post(
            reverse("spatial_analysis_geography_values_api"),
            self.geojson_upload(geography_column="geoid"),
        )
        self.assertEqual(
            geography_response.status_code,
            200,
            geography_response.content,
        )
        self.assertEqual(geography_response.json()["count"], 25)
