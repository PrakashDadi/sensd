"""Configuration for the public spatial-analysis tool catalogue."""

SPATIAL_TOOLS = {
    "risk-map": {
        "title": "Risk Map",
        "tool_name": "salmonella-risk",
        "category": "risk",
        "category_label": "Risk",
        "icon": "bi-shield-check",
        "preview": "mapsapp/images/spatial_tools/risk_map_preview.png",
        "description": "Map standardized disease risk using case and population fields.",
    },
    "bivariate": {
        "title": "Bivariate Analysis",
        "tool_name": "bivariate",
        "category": "association",
        "category_label": "Association",
        "icon": "bi-grid-3x3-gap",
        "preview": "mapsapp/images/spatial_tools/bivariate_map_preview.png",
        "description": "Compare two variables and map their combined spatial pattern.",
    },
    "local-moran": {
        "title": "Hotspot Analysis",
        "tool_name": "local-moran",
        "category": "hotspot",
        "category_label": "Hotspot",
        "icon": "bi-bullseye",
        "preview": "mapsapp/images/spatial_tools/hotspot_map_preview.png",
        "description": "Identify statistically significant clusters and spatial outliers.",
    },
    "spatial-association": {
        "title": "Spatial Association",
        "tool_name": "spatial-association",
        "category": "association",
        "category_label": "Association",
        "icon": "bi-bezier2",
        "preview": "mapsapp/images/spatial_tools/bivariate_moran_preview.png",
        "description": "Measure global and local spatial association between variables.",
    },
    "spatial-regression": {
        "title": "Spatial Regression",
        "tool_name": "spatial-regression",
        "category": "regression",
        "category_label": "Regression",
        "icon": "bi-graph-up-arrow",
        "preview": "mapsapp/images/spatial_tools/spatial_regression_preview.png",
        "description": "Fit regression models and inspect spatial diagnostics.",
    },
}


def spatial_tool_cards():
    """Return template-ready tool records with their URL slugs."""
    return [dict(config, slug=slug) for slug, config in SPATIAL_TOOLS.items()]
