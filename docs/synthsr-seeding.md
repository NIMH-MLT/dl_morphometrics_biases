SynthSR is a deep learning tool that generates a high-resolution 1 mm isotropic T1-weighted image from an input scan of any resolution/contrast. By feeding these SynthSR-derived images into the standard recon-all pipeline, we obtain FreeSurfer results as if the scans were high-quality MPRAGE images. This allows us to assess how the canonical pipeline performs on enhanced inputs and compare results across pipelines.

**We will run recon-all 8 using the synthSR outputs from the following pipelines:**
**- recon-all 8 control (full resolution with T2)**
**- recon-all clinical (run on T1 resampled to 1x1x5)**
**- recon any (run on T1 resampled to 1x1x5)**

The approach for this will be:

- Find each SynthSR.mgz (a brain-extracted 1 mm MRI), something like `.../freesurfer/<pipeline_dir>/sub-12345/ses-ABC/fs_out/sub-12345/mri/SynthSR.mgz`
- Run a freesurfer swarm for each pipeline (name each pipeline by appending `_synthsr` to the original)
    - remember to use -noskullstrip
