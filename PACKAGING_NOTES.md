# Packaging notes

This cleaned GitHub-ready package was assembled from the uploaded `cciot codes.zip` and `main proposed code.zip` archives.

Included:

- `src/`: final implementation modules with CICIoT2023 and UNSW-NB15 support
- `configs/`: main UNSW-NB15 and CICIoT2023 experiment configurations
- `tests/`: unit tests
- `run.py`: main experiment launcher
- `prepare_ciciot2023.py` and `inspect_ciciot2023.py`: CICIoT2023 data utilities
- numbered Windows `.bat` scripts for reproducibility convenience
- `README.md`, `.gitignore`, `CITATION.cff`, and `LICENSE`

Excluded:

- `__pycache__/` and compiled Python files
- temporary logs and review-package scripts
- result ZIPs and generated reports
- raw datasets and heavy output files
- the older `base codes.zip` contents

Before publishing, update `CITATION.cff` with the final GitHub repository URL.
