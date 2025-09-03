#!/usr/bin/env bash

# ----------------------------
# 1) GLOBAL VARIABLES
# ----------------------------

# Base directory where all pipeline folders live
BASEDIR="/data/ABCD_MBDU/ohbm2024/data/derivatives/freesurfer"

# Which subject directory to start from (0-based index)
START=0

# Which MGZ files to try for main volumetric display (in priority order)
MGZ_CANDIDATES=("brain.finalsurfs.mgz" "brainmask.mgz" "T1.mgz")

# Also show aparc+aseg if it exists
APARCASEG="aparc+aseg.mgz"

# ----------------------------
# 2) CAPTURE PIPELINE ARGUMENTS
# ----------------------------
# The user calls this script with something like:
#    ./my_freeview_script.sh "recon-any_t1*"
#
# This loop will expand that pattern (or patterns) against BASEDIR
# and collect valid directories in the array `pipelines`.

if [ $# -lt 1 ]; then
  echo "Usage: $0 <pipeline_glob> [<pipeline_glob2> ...]"
  echo " e.g. $0 \"recon-any_t1*\""
  exit 1
fi

pipelines=()
for pattern in "$@"; do
  # Expand the pattern within BASEDIR
  for d in "$BASEDIR"/$pattern; do
    if [ -d "$d" ]; then
      pipelines+=("$d")
    fi
  done
done

count_pipelines=${#pipelines[@]}
if [ "$count_pipelines" -lt 2 ] || [ "$count_pipelines" -gt 4 ]; then
  echo "ERROR: Found $count_pipelines pipeline directories; only 2 to 4 are supported."
  echo "Pipelines found:"
  printf '  %s\n' "${pipelines[@]}"
  exit 1
fi

echo "Found $count_pipelines pipeline directories:"
printf '  %s\n' "${pipelines[@]}"
echo

# ----------------------------
# 3) GATHER SUBJECTS
# ----------------------------
# We take the first pipeline directory and list the top-level subject folders in it.
pipeline0="${pipelines[0]}"

if [ ! -d "$pipeline0" ]; then
  echo "ERROR: The first pipeline directory doesn't exist: $pipeline0"
  exit 1
fi

subjects=($(ls "$pipeline0"))

# ----------------------------
# 4) LOOP OVER SUBJECTS
# ----------------------------
for (( i=START; i<${#subjects[@]}; i++ )); do
  subj="${subjects[i]}"
  echo "-------------------------------------------------------------------------"
  echo "Subject: $subj"

  # We'll collect a list of freeview arguments (-v or -surface, etc.)
  volume_args=()

  # ----------------------------
  # 4A) LOOP OVER PIPELINES
  # ----------------------------
  for pipeline_dir in "${pipelines[@]}"; do

    # Attempt to find the subject's session directory
    # Example path:
    #   pipeline_dir/sub-NDARINV00HEV6HB/ses-XXXX/fs_out/sub-NDARINV00HEV6HB/mri
    session_path="$(ls -d "$pipeline_dir/$subj"/ses-*/fs_out/"$subj" 2>/dev/null | head -n 1)"

    if [ -z "$session_path" ]; then
      echo "  [WARNING] No session directory for $subj in $pipeline_dir. Skipping."
      continue
    fi

    mri_path="$session_path/mri"
    if [ ! -d "$mri_path" ]; then
      echo "  [WARNING] No mri/ folder for $subj in $pipeline_dir. Skipping."
      continue
    fi

    # 4B) Find an MGZ file (in priority order)
    found_volume=""
    for mgz_file in "${MGZ_CANDIDATES[@]}"; do
      fullpath="$mri_path/$mgz_file"
      if [ -f "$fullpath" ]; then
        found_volume="$fullpath"
        # Construct a layer name from pipeline + mgz_file
        layer_name="$(basename "$pipeline_dir")-$(basename "$mgz_file" .mgz)"
        volume_args+=( "-v" "${found_volume}:name=${layer_name}:grayscale=10,130" )
        break
      fi
    done

    if [ -z "$found_volume" ]; then
      echo "  [WARNING] No candidate MGZ found (brain.finalsurfs.mgz, brainmask.mgz, etc.) for $subj in $pipeline_dir."
    fi

    # 4C) If aparc+aseg exists, add it
    aparc_path="$mri_path/$APARCASEG"
    if [ -f "$aparc_path" ]; then
      layer_name="$(basename "$pipeline_dir")-aparc+aseg"
      volume_args+=(
        "-v" "${aparc_path}:lut=$FREESURFER_HOME/FreeSurferColorLUT.txt:opacity=1:colormap=lut:name=${layer_name}"
      )
    fi

  done  # end pipeline loop

  # If we have no volumes at all, skip launching freeview
  if [ ${#volume_args[@]} -eq 0 ]; then
    echo "  [INFO] No volumes to display for $subj. Skipping freeview."
    continue
  fi

  # ----------------------------
  # 5) LAUNCH FREEVIEW
  # ----------------------------
  echo "  Launching freeview with ${#volume_args[@]} arguments..."
  freeview --hide-3d-slices --view coronal "${volume_args[@]}" &

  # Wait for freeview to close
  wait $!

  echo "  Finished. Press Enter to continue to the next subject."
  read -r
done

echo "All subjects processed."
