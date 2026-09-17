"""Compatibility entry point for Django's app-based test discovery."""

from .test_spatial_analysis import SpatialAlgorithmTests, SpatialApiTests

__all__ = ["SpatialAlgorithmTests", "SpatialApiTests"]
