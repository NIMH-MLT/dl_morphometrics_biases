"""
Data processing utilities for morphometrics analysis.

This module contains reusable functions for processing brain morphometry data,
particularly for handling hemisphere-specific data and region name extraction.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import constants as cfg


def strip_to_hemi(col: str) -> str | None:
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


def parse_bids_ids(
    df: pd.DataFrame,
    participant_col: str = "participant_id",
    session_col: str = "session_id",
) -> pd.DataFrame:
    """
    Parse BIDS participant and session IDs into subject/session columns.

    Args:
        df: DataFrame with BIDS-style participant_id and session_id columns
        participant_col: Name of the participant ID column
        session_col: Name of the session ID column

    Returns:
        DataFrame with added 'subject' and 'session' columns
    """
    df = df.copy()
    df["subject"] = df[participant_col].str.split("-").str[1]
    df["session"] = df[session_col].str.split("-").str[1]
    return df


def load_balanced_scans(bids_dir: Path, project_dir: Path) -> pd.DataFrame:
    """
    Load and prepare balanced scans DataFrame with full paths.

    Args:
        bids_dir: Path to BIDS raw data directory
        project_dir: Path to project directory containing balanced_scans.csv

    Returns:
        DataFrame with balanced scans and full file paths
    """
    balanced_scans = pd.read_csv(project_dir / "code/balanced_scans.csv")
    balanced_scans["path"] = bids_dir / balanced_scans.filename
    return balanced_scans


def prepare_scan_pairs(
    balanced_scans: pd.DataFrame, max_per_session: int = 250
) -> pd.DataFrame:
    """
    Prepare T1w/T2w scan pairs for processing.

    Args:
        balanced_scans: DataFrame from load_balanced_scans()
        max_per_session: Maximum scans per session

    Returns:
        DataFrame with paired T1w/T2w scans
    """
    t1w_scans = (
        balanced_scans.query("modality == 'T1w'")
        .loc[:, ["participant_id", "session_id", "path"]]
        .rename(columns={"path": "t1_path"})
    )

    t2w_scans = (
        balanced_scans.query("modality == 'T2w'")
        .loc[:, ["participant_id", "session_id", "path"]]
        .rename(columns={"path": "t2_path"})
    )

    scans_to_run = t1w_scans.merge(
        t2w_scans, how="left", on=["participant_id", "session_id"]
    )
    scans_to_run = parse_bids_ids(scans_to_run)
    scans_to_run = scans_to_run.groupby("session").head(max_per_session)

    return scans_to_run


def load_session_info() -> pd.DataFrame:
    """
    Load and process session info with age conversion.

    Returns:
        DataFrame with processed session information including age_years
    """
    ses_info = pd.read_csv(cfg.age_tsv, sep="\t")
    ses_info = parse_bids_ids(ses_info)
    ses_info["age_years"] = ses_info.age / 12
    return ses_info


def load_fastages_info() -> pd.DataFrame:
    """
    Load and process fast ages info.

    Returns:
        DataFrame with processed fast ages information
    """
    fastages = pd.read_csv(cfg.fastages_tsv, sep="\t")
    fastages = parse_bids_ids(fastages)
    fastages["age_years"] = fastages.age / 12
    return fastages


def merge_age_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge DataFrame with age data from both session sources.

    Args:
        df: DataFrame with subject/session columns to merge age data into

    Returns:
        DataFrame with age_years column populated
    """
    ses_info = load_session_info()
    fastages = load_fastages_info()

    # Merge with main session info
    with_age = df.merge(
        ses_info.loc[:, cfg.metadata_cols], how="left", on=["subject", "session"]
    )

    # Fill missing ages with fastages data
    with_all_ages = with_age.merge(
        fastages.loc[:, cfg.metadata_cols],
        how="left",
        on=["subject", "session"],
        suffixes=("", "_fa"),
    )
    with_all_ages["age_years"] = with_all_ages.age_years.fillna(
        with_all_ages.age_years_fa
    )

    # Clean up temporary columns
    with_all_ages = with_all_ages.drop(
        columns=[col for col in with_all_ages.columns if col.endswith("_fa")]
    )

    return with_all_ages


def load_brain_confounds(pipeline: str, suffix: str) -> pd.DataFrame:
    """
    Load BrainConfounds.tsv for a specific pipeline with proper column naming.

    Args:
        pipeline: Pipeline name (e.g., 'recon-all', 'recon-all_clinical_t1')
        suffix: Suffix to append to metric columns (e.g., '_ra', '_ract1')

    Returns:
        DataFrame with renamed columns
    """
    fn = cfg.stats_dir / pipeline / "BrainConfounds.tsv"
    df = pd.read_csv(fn, sep="\t")
    df.columns = ["subject", "session"] + [m + suffix for m in cfg.metric_cols]
    return df


def load_and_merge_brain_confounds() -> pd.DataFrame:
    """
    Load and merge all brain confounds data according to pipeline configuration.

    Returns:
        Merged and scaled DataFrame with all pipeline data
    """
    dfs = {}

    for pipeline, suffix, how in cfg.pipelines:
        df = load_brain_confounds(pipeline, suffix)
        dfs[suffix] = (df, how)

    # Merge them in sequence
    merged, _ = dfs["_ra"]  # start with recon-all (_ra)
    for _, suffix, _how in cfg.pipelines[1:]:
        df, merge_how = dfs[suffix]
        merged = merged.merge(df, on=["subject", "session"], how=merge_how)

    # Fix column names
    merged.columns = (
        merged.columns.str.strip().str.replace(r"[\s\-]+", "_", regex=True).str.lower()
    )

    # Scale to 10^5 mm^3
    merged.iloc[:, 2:] /= 10000

    return merged
