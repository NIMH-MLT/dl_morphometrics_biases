# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "freesurfer-stats",
#     "pandas",
# ]
# ///
import argparse
import hashlib
import os
import pickle
import re
import warnings
from pathlib import Path

import pandas as pd
from freesurfer_stats import CorticalParcellationStats as fs

warnings.simplefilter("ignore", FutureWarning)

# ----------------------------------------------------------------------------
# CONSTANTS
# ----------------------------------------------------------------------------
METRIC_MAPPING = {
    "surface_area_mm^2": "SurfaceArea",
    "gray_matter_volume_mm^3": "GrayVol",
    "average_thickness_mm": "ThickAvg",
    "integrated_rectified_mean_curvature_mm^-1": "MeanCurv",
    "integrated_rectified_gaussian_curvature_mm^-2": "GausCurv",
    "folding_index": "FoldInd",
}
HEMIS = ("lh", "rh")
# canonical tokens to match the required descriptions
DEFAULT_BRAIN_METRICS = (
    "SubCortGrayVol,TotalGrayVol,CortexVol,MaskVol,BrainSegVolNotVent,"  # gray & mask
    "lhCerebralWhiteMatterVol,rhCerebralWhiteMatterVol,CerebralWhiteMatterVol"
)
BRAINVOL_NAME = "brainvol.stats"
OUT_SUBDIR = "leej3/fs_stats_multi"

_BV_RE = re.compile(r"^#\s+Measure\s+([^,]+),\s*([^,]+),[^,]*,\s*([0-9.eE+-]+)")

# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Extract aparc + brainvol metrics across multiple pipelines (cached)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("pipeline_roots", help="Comma‑separated pipeline root dirs (first = recon‑all)")
    p.add_argument("--metrics", default=",".join(METRIC_MAPPING.keys()), help="Aparc metrics")
    p.add_argument("--atlases", default=",.a2009s,.DKTatlas", help="Atlas suffix list")
    p.add_argument("--brain-metrics", default=DEFAULT_BRAIN_METRICS, help="Brainvol metrics to keep")
    p.add_argument("--invalidate-cache", action="store_true", help="Recompute cache regardless")
    p.add_argument("--quiet", action="store_true", help="Silence warnings")
    return p.parse_args()

# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------

def aparc_filename(hemi: str, atlas_suffix: str) -> str:
    return f"{hemi}.aparc{atlas_suffix}.stats" if atlas_suffix else f"{hemi}.aparc.stats"


def log(msg: str, quiet: bool):
    if not quiet:
        print(msg)


def cache_filename(parent: Path, pipeline_roots: list[Path]) -> Path:
    digest = hashlib.md5(",".join(map(str, pipeline_roots)).encode()).hexdigest()[:8]
    return parent / f"stats_dir_cache_{digest}.pkl"

# ----------------------------------------------------------------------------
# FIRST PASS – VALID SESSION DISCOVERY
# ----------------------------------------------------------------------------

def compute_valid_sessions(recon_root: Path, pipelines: list[Path], atlases: list[str], quiet: bool):
    warned_dirs, warned_sess = set(), set()
    valid: dict[tuple[str, str], dict[Path, Path]] = {}
    for sub_dir in recon_root.glob("sub-*"):
        sub_name = sub_dir.name; sub_id = sub_name.split("-", 1)[1]
        for ses_dir in sub_dir.glob("ses-*"):
            ses_name = ses_dir.name; ses_id = ses_name.split("-", 1)[1]
            combo_ok, sd_map = True, {}
            for pr in pipelines:
                sd = pr / sub_name / ses_name / "fs_out" / sub_name / "stats"
                if not sd.is_dir():
                    if sd not in warned_dirs:
                        log(f"Stats dir missing: {sd}", quiet); warned_dirs.add(sd)
                    combo_ok = False; break
                present = {f.name for f in sd.iterdir()}
                if not all(all(aparc_filename(h, a) in present for h in HEMIS) for a in atlases):
                    if (sub_id, ses_id) not in warned_sess:
                        log(f"Incomplete aparc: {sd}", quiet); warned_sess.add((sub_id, ses_id))
                    combo_ok = False; break
                if BRAINVOL_NAME not in present:
                    if (sub_id, ses_id) not in warned_sess:
                        log(f"Missing brainvol.stats: {sd}", quiet); warned_sess.add((sub_id, ses_id))
                    combo_ok = False; break
                sd_map[pr] = sd
            if combo_ok:
                valid[(sub_id, ses_id)] = sd_map
    return valid

# ----------------------------------------------------------------------------
# BRAINVOL PARSER
# ----------------------------------------------------------------------------

def parse_brainvol(bv_path: Path, keep: set[str]):
    rows = []
    try:
        with bv_path.open() as fh:
            for line in fh:
                m = _BV_RE.match(line)
                if not m:
                    continue
                tok1, tok2, value = m.groups()
                canonical = tok2.strip() if tok2.strip() in keep else tok1.strip()
                if canonical in keep:
                    rows.append((canonical, float(value)))
    except FileNotFoundError:
        return None
    if not rows:
        return None
    return pd.DataFrame(rows, columns=["Measure", "Value"])

# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------

def main() -> None:
    args = parse_args(); quiet = args.quiet
    atlases = args.atlases.split(","); aparc_metrics = args.metrics.split(",")
    brain_keep = set(args.brain_metrics.split(","))

    pipelines = [Path(p).resolve() for p in args.pipeline_roots.split(",")]
    recon_root = pipelines[0]
    print(f"recon root: {recon_root}")

    out_parent = recon_root.parents[1] / OUT_SUBDIR; out_parent.mkdir(parents=True, exist_ok=True)
    cache_path = cache_filename(out_parent, pipelines)

    if cache_path.exists() and not args.invalidate_cache:
        cache_obj = pickle.load(cache_path.open("rb"))
        valid_sessions = {tuple(k): {Path(pk): Path(sd) for pk, sd in v.items()} for k, v in cache_obj["sessions"].items()}
        log("Loaded stats_dir cache", quiet)
    else:
        valid_sessions = compute_valid_sessions(recon_root, pipelines, atlases, quiet)
        pickle.dump({"sessions": {k: {str(pk): str(sd) for pk, sd in v.items()} for k, v in valid_sessions.items()}}, cache_path.open("wb"))
        log("Wrote new stats_dir cache", quiet)

    # prepare accumulators
    aparc_rows = {pr: {a: {m: [] for m in aparc_metrics} for a in atlases} for pr in pipelines}
    brain_rows = {pr: [] for pr in pipelines}
    full_bv_cols = ["subject", "session", *sorted(brain_keep)]

    # second pass – read data
    for (sub_id, ses_id), pr_map in valid_sessions.items():
        for pr, sd in pr_map.items():
            # brainvol
            bv_df = parse_brainvol(sd / BRAINVOL_NAME, brain_keep)
            if bv_df is not None:
                bv_df["subject"], bv_df["session"] = sub_id, ses_id
                pivot = (
                    bv_df.pivot(index=["subject", "session"], columns="Measure", values="Value")
                    .reset_index()
                ).reindex(columns=full_bv_cols, fill_value=pd.NA)
                brain_rows[pr].append(pivot)
            # aparc
            for atlas_key in atlases:
                lh = fs.read(str(sd / aparc_filename("lh", atlas_key))).structural_measurements
                rh = fs.read(str(sd / aparc_filename("rh", atlas_key))).structural_measurements
                lh_p = lh.assign(structure_name=lambda d: d["structure_name"]+"_lh").set_index("structure_name")[aparc_metrics].T
                rh_p = rh.assign(structure_name=lambda d: d["structure_name"]+"_rh").set_index("structure_name")[aparc_metrics].T
                for metric in aparc_metrics:
                    aparc_rows[pr][atlas_key][metric].append({
                        "subject": sub_id,
                        "session": ses_id,
                        **lh_p.loc[metric].to_dict(),
                        **rh_p.loc[metric].to_dict(),
                    })

    # write outputs
    for pr in pipelines:
        out_dir = out_parent / pr.name; out_dir.mkdir(parents=True, exist_ok=True)
        # brainconfounds
        if brain_rows[pr]:
            pd.concat(brain_rows[pr], ignore_index=True).to_csv(out_dir / "BrainConfounds.tsv", sep="\t", index=False)
                # aparc TSVs
        for atlas_key, metric_map in aparc_rows[pr].items():
            atlas_name = atlas_key or "Desikan2006"
            for metric, rows in metric_map.items():
                if not rows:
                    continue
                df = pd.DataFrame.from_records(rows)
                ordered_cols = ["subject", "session", *[c for c in df.columns if c not in {"subject", "session"}]]
                df = df[ordered_cols]
                df.to_csv(out_dir / f"atlas-{atlas_name}_{METRIC_MAPPING.get(metric, metric)}.tsv", sep="	", index=False)


if __name__ == "__main__":
    main()
