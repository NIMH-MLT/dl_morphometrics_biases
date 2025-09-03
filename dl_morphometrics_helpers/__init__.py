"""
dl_morphometrics_helpers: Reusable utilities for deep learning morphometrics analysis.

This package provides common functionality for processing FreeSurfer outputs,
handling brain morphometric data, and supporting reproducible analyses.
"""

__version__ = "0.1.0"

# Import main utilities for easy access
from .data_processing import strip_to_hemi, get_region_names
from .constants import (
    brain_metrics,
    metadata_cols,
    atlases,
    pipelines,
    diff_specs,
    comparison_labels,
    metric_cols,
    metric_contractions,
)

__all__ = [
    "strip_to_hemi",
    "get_region_names",
    "brain_metrics",
    "metadata_cols",
    "atlases",
    "pipelines",
    "diff_specs",
    "comparison_labels",
    "metric_cols",
    "metric_contractions",
]
