from pathlib import Path
from typing import Set, Optional
import re
import pandas as pd
#
# definitions and parameters
#

# where are files, and where will processed files go
project_dir = Path("/data/ABCD_MBDU/ohbm2024/")
drv_dir   = project_dir / 'data/derivatives/'
stats_dir = drv_dir / "leej3/fs_stats_multi"
tpl_root = project_dir / "templateflow" / "tpl-fsaverage"
age_tsv = '/data/ABCD_DSST/ABCD/imaging_data/fast_track/sessions.tsv'
fastages_tsv = '/data/ABCD_DSST/ABCD/imaging_data/fast_track/code/abcd_fastqc01_history/2024-05-01/abcd_fastqc01_ages_innerjoin_sessions_without_age.tsv'


brain_metrics = ['surface_area_mm^2',
                 'gray_matter_volume_mm^3',
                 'average_thickness_mm',
                 'integrated_rectified_mean_curvature_mm^-1',
                 'integrated_rectified_gaussian_curvature_mm^-2',
                 'folding_index']

metadata_cols = ['subject', 'session', 'age_years','site_id']


def strip_to_hemi(col: str) -> Optional[str]:
    """
    If `col` contains '_lh' or '_rh', return everything
    up through that hemisphere tag. Otherwise return None.
    """
    for hemi in ('_lh', '_rh'):
        idx = col.find(hemi)
        if idx != -1:
            # +len(hemi) to include '_lh' / '_rh' itself
            return col[: idx + len(hemi)]
    return None

def get_region_names(df: pd.DataFrame) -> Set[str]:
    """
    Extract the set of region names (ending in _lh or _rh)
    from df.columns, stripping off any trailing diff‐suffixes.
    """
    regions = {
        stripped
        for col in df.columns
        if (stripped := strip_to_hemi(col)) is not None
    }
    return regions

atlases = ['', '.a2009s', '.DKTatlas']

# pipeline → suffix → merge strategy
pipelines = [
    ('recon-all',                       '_ra',      'inner'),
    # ('recon-all-8',                       '_ra8',      'inner'),
    ('recon-all_clinical_t1',          '_ract1',   'inner'),
    ('recon-all_clinical_t2',          '_ract2',   'inner'),
    ('recon-all_clinical_t1_resample-3','_ract1r3','inner'),
    ('recon-all_clinical_t1_resample-5','_ract1r5','inner'),
    # ('recon-all_not2',                  '_ranot2',  'inner'),
    ("recon-any_t2",'_ranyt2','inner'),
    ("recon-any_t1",'_ranyt1','inner'),

    ("recon-any_t1_resample-3",'_ranyt1r3','inner'),
    ("recon-any_t1_resample-5",'_ranyt1r5','inner'),
    
]
path_inputs  = [drv_dir / 'freesurfer' / p[0] for p in pipelines]

# define which columns to compare and what suffix to give the new pct‐diff cols
diff_specs = {
    # key: (base_suffix, comp_suffix)
    # 'all8':    ('_ra',      '_ra8'),
    'ct1':    ('_ra',      '_ract1'),
    'ct2':    ('_ra',      '_ract2'),
    'ct1r3':  ('_ra',      '_ract1r3'),
    'ct1r5':  ('_ra',      '_ract1r5'),
    'ct1ct2': ('_ract1',   '_ract2'),

    # 'not2':   ('_ra',      '_ranot2'), # causes zero variance issues in modelling
    
    'anyt1':    ('_ra',      '_ranyt1'),
    'anyt2':    ('_ra',      '_ranyt2'),
    'anyt1r3':    ('_ra',      '_ranyt1r3'),
    'anyt1r5':    ('_ra',      '_ranyt1r5'),
    'any1any2':    ('_ranyt1',      '_ranyt2'),
}
comparison_labels = {
    # key: LABEL
    'all8':    'RA_7-vs-8',
    'ct1':    'RAC_T1',
    'ct2':    'RAC_T2',
    'ct1r3':  'RAC_T1-R3',
    'ct1r5':  'RAC_T1-R5',
    'ct1ct2': 'RAC_T1_vs_T2',
    'not2':   'RAC_not2',
    'anyt1':  'RANY_T1',
    'anyt2':  'RANY_T2',
    'anyt1r3': 'RANY_T1-R3',
    'anyt1r5': 'RANY_T1-R5',
    'any1any2': 'RANY_T1-vs-T2',
}

# RAC / RANY split
rac_groups  = ["ct1", "ct1r3", "ct1r5", "ct2", "ct1ct2"]
rany_groups = ["anyt1", "anyt1r3", "anyt1r5", "anyt2", "any1any2"]


# header for confounds tsvs (do not change)
metric_cols = global_metric = [
    'Brain Segmentation Volume Without Ventricles',
    'Total cerebral white matter volume',
    'Total cortical gray matter volume',
    'Mask Volume',
    'Subcortical gray matter volume',
    'Total gray matter volume',
    'Left hemisphere cerebral white matter volume',
    'Right hemisphere cerebral white matter volume',
]

metric_cols_nospace = [mc.strip().lower().replace(' ', '_') for mc in metric_cols]

metric_contractions = {
    'total_cortical_gray_matter_volume':'Cort_GMV',
     'total_cerebral_white_matter_volume':"Cereb_WMV",
    'subcortical_gray_matter_volume':'Subcort_GMV',
     # 'total_gray_matter_volume',
     
     # 'mask_volume',
     # 'brain_segmentation_volume_without_ventricles',
     # 'left_hemisphere_cerebral_white_matter_volume',
     # 'right_hemisphere_cerebral_white_matter_volume',

}
