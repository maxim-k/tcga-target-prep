# Semantic QC — gene filtering / HVG threshold derivation

2026-08-13. Backs the `2026-08-13 — Semantic QC` section of
`lab_notebook.ipynb`. This is the noise-filtering/HVG-selection methodology
for the exploratory clustering/PCA/UMAP pipeline specifically — separate from
ARACNe/VIPER input prep, see the scope note in
`supplementary/aracne_viper_data_prep_research.md`.

## Why a computed threshold instead of an assumed one

The brief for this step explicitly required looking at the actual count
distribution and deciding a threshold from it, not assuming a round number
up front. Numbers below are computed directly against
`processed/expression/tcga_target_raw.h5ad` (14,336 survivors, 60,660 genes,
`layers["tpm"]`), reproduced live in the notebook cell that uses them.

## Detection-rate noise floor

Fraction of the 14,336 survivors with TPM > 1, per gene:

| Statistic | Value |
|---|---|
| Genes with 0% detection (never TPM>1 in any sample) | 2,944 |
| Genes with <1% detection | 15,243 |
| Median gene | 11% detection |
| Genes with <10% detection | 29,642 |
| Genes with ≥10% detection | 31,018 |

The distribution is sharply bimodal — most genes are either broadly detected
or essentially never detected, with comparatively few in between. A 10%
detection floor sits in that gap and removes the "never really expressed"
half of the transcriptome (29,642 genes) without touching genes that are
real signal in a specific subset of samples (e.g. a gene expressed only in
one rare disease's ~12-88 samples can still clear a 10%-of-14,336 ≈ 1,434
sample floor only if it's genuinely broadly detected — a stricter
per-disease floor was considered and rejected here because this filtering
step operates on the pooled cohort before any per-disease analysis, and the
disease-level heatmap/centroid analysis downstream is exactly what surfaces
disease-specific genes on its own terms).

## Variance ranking and knee detection

Among the 31,018 genes clearing the detection floor, variance of
log2(TPM+1) ranges from near 0 to 22.5, median 1.00 — a long right tail,
consistent with "most genes are fairly stable, a subset carries most of the
biological variance," which is exactly the shape HVG selection targets.

Ranking these 31,018 genes by variance (descending) and applying kneedle-style
knee detection (max perpendicular distance from the straight line connecting
the sorted curve's first and last point, on min-max-normalized rank and
value) lands the knee at **rank 2,185, variance 3.62**.

Reference points on the same curve, for context:

| Top-N genes | Variance cutoff at that rank |
|---:|---:|
| 500 | 6.48 |
| 1,000 | 4.96 |
| 1,500 | 4.25 |
| 2,000 | 3.77 |
| **2,185 (knee)** | **3.62** |
| 2,500 | 3.42 |
| 3,000 | 3.13 |
| 4,000 | 2.71 |
| 5,000 | 2.40 |
| 8,000 | 1.76 |
| 10,000 | 1.47 |

The knee landing near the "2,000-3,000" range mentioned in an early,
disclaimed rough sketch from the start of this project is coincidental — it
falls out of the actual shape of this dataset's variance curve, not from
that number being assumed going in. The notebook renders this curve with the
knee marked so the cutoff is visually checkable, not just a printed number.

## OncoTree disease grouping (2026-08-14)

Every disease-colored PCA/UMAP plot originally used one 42-color legend —
past the ~7-10 hues a legend can actually communicate. Fixed with a 12-panel
small-multiples grid (`ONCOTREE_GROUP` in `scripts/build_sample_breakdown.py`,
`grouped_scatter_grid()` in the notebook): full dataset in gray per panel,
that panel's diseases highlighted in a small qualitative palette on top.

The mapping is **manually curated**, not automated code-matching. Checked
the real OncoTree API (`oncotree.mskcc.org/api/tumorTypes`) and found a
genuine collision: OncoTree's own code `TGCT` is *Tenosynovial Giant Cell
Tumor* (soft tissue) — completely unrelated to TCGA's `TGCT` (*Testicular
Germ Cell Tumors*, confirmed against `tcga_code_tables/diseaseStudy.tsv`).
Matching by string alone would have silently placed testicular cancer in a
soft-tissue sarcoma panel. Every code in the mapping was instead checked
against its already-verified full disease name, using OncoTree's tissue
*names* as the grouping vocabulary.

12 panels, all ≤7 diseases: Kidney (6), Myeloid leukemia (2), Lymphoid
leukemia/lymphoma (4), CNS/Brain (2), Lung (2), Pan-GI (7), Pan-Gyn (4),
Genitourinary (3), Endocrine (3), Melanoma (2), Breast (1), Other solid (6).
"Pan-GI"/"Pan-Gyn"/"Genitourinary"/"Endocrine"/"Melanoma" are standard
clinical/genomics groupings merging adjacent OncoTree tissues (e.g. Pan-GI =
Bowel + Esophagus/Stomach + Liver + Biliary Tract + Pancreas), labeled as
merges rather than presented as literal OncoTree categories. "Other solid"
(Soft Tissue, Bone, Peripheral Nervous System, Pleura, Head and Neck,
Thymus) is an honest catch-all for sites with no natural partner among these
42 codes, not a fake coherent label.
