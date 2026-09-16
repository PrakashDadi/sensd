from django.urls import path

from . import spatial_views, views

urlpatterns = [
    path("gis-home/", views.home, name="gis-home"),
    path("gis-dashboard/", views.gis_dashboard, name="gis_dashboard"),
    path("maps/", views.maps_view, name="maps_view"),
    path("grid/", views.grid_view, name="grid_view"),
    path("data-mapping/", views.data_mapping_tool_view, name="data_mapping_tool"),
    path("flow_analysis/", views.flow_analysis_view, name="flow_analysis"),
    path(
        "spatial-analysis/",
        spatial_views.flow_analysis_view,
        name="spatial_analysis",
    ),
    path(
        "api/spatial/inspect-columns/",
        spatial_views.inspect_columns_api,
        name="spatial_inspect_columns_api",
    ),
    path(
        "api/spatial/upload-flow/",
        spatial_views.upload_flow_api,
        name="spatial_upload_flow_api",
    ),
    path(
        "api/spatial/upload-reference/",
        spatial_views.upload_reference_api,
        name="spatial_upload_reference_api",
    ),
    path(
        "api/spatial/salmonella-risk-map/",
        spatial_views.salmonella_risk_map_api,
        name="spatial_salmonella_risk_map_api",
    ),
    path(
        "api/spatial/bivariate-map/",
        spatial_views.bivariate_map_api,
        name="spatial_bivariate_map_api",
    ),
    path(
        "api/spatial/local-moran/",
        spatial_views.local_moran_api,
        name="spatial_local_moran_api",
    ),
    path(
        "api/spatial/spatial-association/",
        spatial_views.spatial_association_api,
        name="spatial_association_api",
    ),
    path(
        "api/spatial/spatial-regression/",
        spatial_views.spatial_regression_api,
        name="spatial_regression_api",
    ),
    path(
        "api/spatial/county-salmonella-risk/",
        spatial_views.county_salmonella_risk_api,
        name="spatial_county_salmonella_risk_api",
    ),
    path(
        "api/spatial/geography-values/",
        spatial_views.analysis_geography_values_api,
        name="spatial_analysis_geography_values_api",
    ),
    path("api/walmart/", views.walmart_geojson, name="walmart_geojson"),
    path("api/schnucks/", views.schnucks_geojson, name="schnucks_geojson"),
    path("api/save_a_lot/", views.save_a_lot_geojson, name="save_a_lot_geojson"),
    path("api/whole_foods/", views.whole_foods_geojson, name="whole_foods_geojson"),
    path(
        "api/fsis_coordinates/",
        views.fsis_coordinates_geojson,
        name="fsis_coordinates_geojson",
    ),
    path(
        "api/county_bivariate/",
        views.county_bivariate_geojson,
        name="county_bivariate_geojson",
    ),
    path("api/us_states/", views.us_states_geojson, name="us_states_geojson"),
    path(
        "api/flow_with_quantity/",
        views.flow_with_quantity_geojson,
        name="flow_with_quantity_geojson",
    ),
    path("api/upload_flow/", views.upload_flow_api, name="upload_flow_api"),
    path(
        "api/flow_line_quantity/",
        views.flow_line_quantity_geojson,
        name="flow_line_quantity_geojson",
    ),
    path("api/upload/", views.upload_data_api, name="upload_data_api"),
    path("api/layers/", views.list_user_layers_api, name="list_user_layers_api"),
    path(
        "api/layers/<int:layer_id>/",
        views.get_layer_geojson_api,
        name="get_layer_geojson_api",
    ),
    path(
        "api/layers/<int:layer_id>/delete/",
        views.delete_layer_api,
        name="delete_layer_api",
    ),
]
