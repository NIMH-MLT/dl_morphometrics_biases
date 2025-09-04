from pathlib import Path


def build_fs_swarm_cmd(
    cmds,
    *,
    test=True,
    # Naming
    pipeline_version,
    pipeline_dirname=None,  # Directory name for pipeline (if different from pipeline_version)
    run_tag="fs-8-leej3",  # e.g., "fs-8-leej3" or "fs-8-rerun-leej3"
    # Resources
    ncpus=16,
    g_mem=100,  # GB for -g
    lscratch=400,  # GB local scratch
    time="12:00:00",  # e.g., "12:00:00" or "2-12:00:00"
    partition="norm",
    # Modules
    freesurfer_module_version="freesurfer/7.4.1",
    extra_modules=("fsl",),  # extra modules to load along with freesurfer
    # I/O
    swarm_cmd_dir=Path("./swarm_cmds"),
    swarm_log_dir=Path("./swarm_logs"),
):
    """
    Consolidated swarm command builder for FreeSurfer jobs.

    Args:
        cmds: List of command strings to execute
        test: If True, writes only the first two commands and appends '-test' to job name
        pipeline_version: Version identifier for the pipeline (used in job naming)
        pipeline_dirname: Directory name for pipeline outputs (defaults to pipeline_version if not provided)
        run_tag: Tag to distinguish different runs (e.g., 'fs-8-leej3', 'fs-8-rerun-leej3')
        ncpus: Number of CPUs to request per job
        g_mem: Memory in GB to request per job
        lscratch: Local scratch space in GB to request per job
        time: Wall time limit (e.g., '12:00:00' or '2-12:00:00')
        partition: SLURM partition to submit to
        freesurfer_module_version: FreeSurfer module version to load
        extra_modules: Additional modules to load alongside FreeSurfer
        swarm_cmd_dir: Directory to write swarm command files
        swarm_log_dir: Directory for swarm log files

    Returns:
        Single-line swarm command string ready to copy/paste

    Notes:
        - Creates `swarm_cmd_dir` and `swarm_log_dir` if they don't exist
        - Uses `pipeline_dirname` for directory structure if provided, otherwise uses `pipeline_version`
    """
    # Determine effective pipeline directory name

    # Build job/run name using pipeline_version (for consistency with existing naming)
    run_name = f"abcd_recon_{pipeline_version}-{run_tag}{'-test' if test else ''}"

    # Ensure directories exist
    swarm_cmd_dir.mkdir(parents=True, exist_ok=True)
    swarm_log_dir.mkdir(parents=True, exist_ok=True)

    # Write swarm command file
    swarm_cmd_file = swarm_cmd_dir / run_name
    to_write = cmds[:2] if test else cmds
    swarm_cmd_file.write_text("\n".join(to_write) + "\n")

    # Build module string
    modules = (
        [freesurfer_module_version, *extra_modules]
        if extra_modules
        else [freesurfer_module_version]
    )
    module_arg = ",".join(modules)

    # Compose single-line swarm command (no leading spaces/newlines)
    swarm_exec = (
        f"swarm -f {swarm_cmd_file.resolve()} "
        f"-g {g_mem} -t {ncpus} --gres=lscratch:{lscratch} "
        f"--module {module_arg} --time {time} "
        f"--logdir {swarm_log_dir.resolve()} --job-name {run_name} "
        f"--partition {partition}"
    )

    return swarm_exec
