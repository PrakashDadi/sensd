"""Compatibility entry point for Django's app-based test discovery."""

from django.test import TestCase
from django.urls import reverse

from authentication.models import CustomUser

from .test_spatial_analysis import SpatialAlgorithmTests, SpatialApiTests

__all__ = ["SpatialAlgorithmTests", "SpatialApiTests"]


class GisWorkspaceNavigationTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="gis-navigation-user",
            email="gis-navigation@example.test",
            password="test-password-only",
        )
        self.client.force_login(self.user)

    def test_gis_overview_presents_every_workspace_tool(self):
        response = self.client.get(reverse("gis-home"))
        self.assertEqual(response.status_code, 200)
        for label in ("Location and County Map", "Network and Flow Map", "Flow Analysis", "Spatial Analysis", "Data Mapping", "Spatial Analysis Tools"):
            self.assertContains(response, label)

    def test_gis_workspace_routes_keep_existing_destinations(self):
        for route_name in ("gis-home", "gis_dashboard", "maps_view", "flow_analysis", "spatial_analysis", "data_mapping_tool", "grid_view"):
            response = self.client.get(reverse(route_name))
            self.assertEqual(response.status_code, 200, route_name)
            self.assertContains(response, "GIS workspace navigation")
