from django.urls import path
from . import views

urlpatterns = [
    path('gis-home/', views.home, name='gis-home'),
    path('gis-dashboard/', views.gis_dashboard, name='gis_dashboard'),

    path('api/walmart/', views.walmart_geojson, name='walmart_geojson'),
    path('api/schnucks/', views.schnucks_geojson, name='schnucks_geojson'),
    path('api/save_a_lot/', views.save_a_lot_geojson, name='save_a_lot_geojson'),
    path('api/whole_foods/', views.whole_foods_geojson,
         name='whole_foods_geojson'),
    path('api/fsis_coordinates/', views.fsis_coordinates_geojson,
         name='fsis_coordinates_geojson'),
    path('api/county_bivariate/', views.county_bivariate_geojson,
         name='county_bivariate_geojson'),
    path('api/us_states/', views.us_states_geojson, name='us_states_geojson'),
]
