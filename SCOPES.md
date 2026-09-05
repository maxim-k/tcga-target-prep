# Commit scopes

- `data`: raw GDC acquisition -- manifest, sample sheet, `gdc-client` download run
- `metadata`: barcode decoding and QC-annotation aggregation into the sample metadata table
- `qc`: technical QC filtering and candidate-drop classification
- `expression`: master raw-counts/TPM expression matrix build
- `semantic-qc`: exploratory clustering / batch-effect analysis branch
- `aracne`: ARACNe/VIPER input base matrix (protein-coding filter, CPM, OncoTree tagging)
- `notebook`: `lab_notebook.ipynb` structure, style, or authoring workflow
- `scripts`: `scripts/` helper modules
- `docs`: README, CLAUDE.md, `supplementary/` research notes
- `deps`: `pyproject.toml`, `uv.lock`, Python version
- `repo`: repo-wide config not tied to one pipeline stage (`.gitignore`, git setup)
