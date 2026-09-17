from django.conf import settings


def map_tile_config(request):
    """Expose the optional, environment-configured basemap to map templates."""
    return {
        "map_tile_config": {
            "url": settings.MAP_TILE_URL,
            "attribution": settings.MAP_TILE_ATTRIBUTION,
            "maxZoom": settings.MAP_TILE_MAX_ZOOM,
        }
    }
