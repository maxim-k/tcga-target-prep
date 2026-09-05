# TCGA + TARGET RNA-seq prep for ARACNe / VIPER

RNA-seq gene counts from TCGA and TARGET (GDC STAR pipeline, 15,879 files),
cleaned and assembled into a single expression matrix for ARACNe
disease-specific regulon reconstruction and as a VIPER reference cohort.

**`lab_notebook.ipynb`** tracks all work as a running log.
Read its Abstract cell (cell 0) first -- it's the authoritative, up-to-date
summary of the pipeline and its findings. This README is a map to the repo,
not a substitute for the notebook.

## Pipeline

1. **Acquisition + metadata.** 15,879 files downloaded via `gdc-client` into
   `downloads/` (fixed, read-only from here on). Barcodes decoded against
   `tcga_code_tables/`; per-file `annotations.txt` QC notes aggregated.
   -> `processed/metadata/sample_metadata.parquet`
2. **Technical QC.** Every QC-flagged file (failed
   center QC, DNU, low quality, FFPE preservation, cell lines,
   adjacent-normal, tumor/normal mislabeling) dropped as a hard filter.
   1,543 killed, 14,336 survive.
3. **Master expression matrix.** Raw counts + TPM for all 14,336 survivors,
   full 60,660-gene resolution.
   -> `processed/expression/tcga_target_raw.h5ad` (untouched once built)
4. **Semantic QC** (exploratory, not part of the ARACNe lineage). Does the
   data cluster by biology or by batch? HVG selection, PCA, UMAP, k-means,
   hierarchical clustering, and quantitative batch-effect metrics (LISI,
   kBET-style test) against center/program/disease labels.
   -> `processed/semantic_qc/`
5. **ARACNe base matrix.** Protein-coding genes only, pseudoautosomal
   duplicates collapsed, CPM computed with the full 60,660-gene library
   size as denominator, tagged with both `Project ID` (42 values) and
   `OncoTree Group` (12 tissue-lineage groups) for slicing into
   disease-specific regulons later.
   -> `processed/expression/tcga_target_aracne_base.h5ad`

TMM normalization and per-disease slicing are deliberately **not** done
here -- they depend on which cohort a given ARACNe run targets, so they
happen per-slice, later.

## Layout

```
downloads/          raw GDC download, read-only source of truth (gitignored)
processed/           everything derived from downloads/ (gitignored)
  metadata/           sample metadata table, QC summaries
  expression/          tcga_target_raw.h5ad, tcga_target_aracne_base.h5ad
  semantic_qc/          exploratory clustering outputs + figures
scripts/            barcode decoding, OncoTree mapping, download organizing
tcga_code_tables/   GDC code tables (disease, sample type, center, ...)
supplementary/      research notes referenced from the notebook
lab_notebook.ipynb  the pipeline, in order, with findings
```

`.gitignore` excludes `downloads/` and `processed/` -- both are large
(63 GB / 5 GB) and regenerable: `downloads/` from the GDC manifest,
`processed/` from `downloads/` by re-running the notebook.

## Running

```
uv sync
uv run jupyter nbconvert --execute --to notebook --inplace \
  --ExecutePreprocessor.kernel_name=python3 lab_notebook.ipynb
```
