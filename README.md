# Deep Learning Morphometrics Biases Analysis

This repository contains tools and analyses for studying biases in deep learning approaches to brain morphometrics, with a focus on FreeSurfer pipeline comparisons.

## Repository Structure

```
dl_morphometrics_biases/
├── dl_morphometrics_helpers/     # Reusable package code
│   ├── __init__.py              # Package initialization and exports
│   ├── constants.py             # Configuration constants and parameters
│   └── data_processing.py       # Utility functions for data processing
├── notebooks/                   # Jupyter notebooks for analysis
│   ├── check_numbers.ipynb
│   ├── exploration-recon-any-swarm.ipynb
│   ├── figures.ipynb           # Main figure generation
│   ├── process_freesurfer_recon-any.ipynb
│   ├── run_freesurfer.ipynb
│   └── run_freesurfer8-recon-all.ipynb
├── scripts/                     # Executable scripts
│   ├── fsstats_extraction.py   # CLI tool for FreeSurfer stats extraction
│   └── comparison_script.sh    # FreeSurfer comparison visualization
├── output/                      # Generated outputs
│   └── images/                 # Figure outputs (PNG, PDF)
├── pyproject.toml              # Package configuration
├── .pre-commit-config.yaml     # Code quality hooks
├── .gitattributes             # Git filter configuration
└── README.md                   # This file
```

## Environment Management with UV

This project uses [uv](https://github.com/astral-sh/uv) for fast, reliable Python environment management.

### Installation

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the package in development mode with all dependencies
uv sync --all-extras
```

### Running Scripts

Scripts in the `scripts/` directory use uv's inline dependency specification:

```bash
# Run the FreeSurfer stats extraction script
uv run scripts/fsstats_extraction.py --help

# The script will automatically install its dependencies as needed
```

### Running Notebooks

```bash
# Start JupyterLab with all analysis dependencies
uv run jupyter lab
```

## Development Workflow

### Code Quality

This repository uses automated code quality tools:

- **nbstripout**: Configured as a git filter to automatically strip notebook outputs
- **pre-commit**: Runs ruff, trailing whitespace fixes, and other checks
- **ruff**: Fast Python linting and formatting

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run all checks manually
uv run pre-commit run --all-files
```

### Package Development

The `dl_morphometrics_helpers` package contains reusable utilities:

- Keep dependencies minimal in `pyproject.toml`
- Add new functionality to the appropriate module
- Use type hints and docstrings
- Test functions before using in notebooks

### Dependency Management

**Keep `pyproject.toml` dependencies minimal!**

- Core package dependencies: Only pandas, numpy
- Analysis dependencies: In `[project.optional-dependencies.analysis]`
- Script dependencies: Use uv's inline syntax in script headers
- Development tools: In `[project.optional-dependencies.dev]`

## Git Configuration

### Notebook Output Stripping

This repository uses nbstripout as a git filter (not a pre-commit hook) to avoid working copy modification issues. The configuration is already set up in `.gitattributes`.

If you need to manually configure nbstripout:

```bash
git config filter.nbstripout.clean 'nbstripout'
git config filter.nbstripout.smudge cat
git config filter.nbstripout.required true
git config diff.ipynb.textconv 'nbstripout -t'
```

## Analysis Pipeline

1. **Stats Extraction**:  `scripts/fsstats_extraction.py` to extract FreeSurfer statistics (tricky dependencies involved)
2. **Other exploration/figures**: Run notebooks in `notebooks/`
3. **Outputs**: Most results saved to `output/` directory, figures to `output/images/`
4. **Swarm output**: Larger datasets (freesurfer derivatives, swarm files etc.) are stored in the appropriate cluster dirs.

## Contributing

- Follow the established directory structure
- Use uv for dependency management
- Keep package dependencies minimal
- Add comprehensive docstrings to new functions
- Test notebook changes before committing
- Use the pre-commit hooks to maintain code quality

## Notes

- This repository focuses on FreeSurfer pipeline comparisons and morphometric bias analysis
- Original data paths may need adjustment for your local environment
- See individual notebooks for specific analysis documentation
