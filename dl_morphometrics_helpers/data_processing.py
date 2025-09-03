"""
Data processing utilities for morphometrics analysis.

This module contains reusable functions for processing brain morphometry data,
particularly for handling hemisphere-specific data and region name extraction.
"""

from typing import Optional

import pandas as pd


def strip_to_hemi(col: str) -> Optional[str]:
    """
    If `col` contains '_lh' or '_rh', return everything
    up through that hemisphere tag. Otherwise return None.

    Args:
        col: Column name to check for hemisphere suffix

    Returns:
        String up to and including hemisphere tag, or None if no hemisphere found

    Examples:
        >>> strip_to_hemi("frontal_cortex_lh_thickness")
        'frontal_cortex_lh'
        >>> strip_to_hemi("total_volume")
        None
    """
    for hemi in ("_lh", "_rh"):
        idx = col.find(hemi)
        if idx != -1:
            # +len(hemi) to include '_lh' / '_rh' itself
            return col[: idx + len(hemi)]
    return None


def get_region_names(df: pd.DataFrame) -> set[str]:
    """
    Extract the set of region names (ending in _lh or _rh)
    from df.columns, stripping off any trailing diff‐suffixes.

    Args:
        df: DataFrame with column names that may contain hemisphere suffixes

    Returns:
        Set of unique region names with hemisphere suffixes

    Examples:
        >>> df = pd.DataFrame(columns=["frontal_lh", "frontal_rh", "age", "frontal_lh_diff"])
        >>> get_region_names(df)
        {'frontal_lh', 'frontal_rh'}
    """
    regions = {
        stripped for col in df.columns if (stripped := strip_to_hemi(col)) is not None
    }
    return regions
