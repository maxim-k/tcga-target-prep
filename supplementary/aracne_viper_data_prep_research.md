# ARACNe/VIPER data-prep research

2026-08-13. Backs the normalization decisions applied starting in the
`2026-08-13` section of `lab_notebook.ipynb`. Sources: PDFs in
`/Users/mkuleshov/mskcc/VIPER_project/repos/info/` and the working pipeline at
`/Users/mkuleshov/mskcc/VIPER_project/repos/osteosarcoma_wgts`.

**Scope note:** this document is about ARACNe/VIPER input prep only. Those
matrices stay full-resolution and unfiltered — no HVG selection, no noise
filtering, no downsampling. HVG selection, noise-floor filtering, and
class-imbalance handling are a *separate* pipeline (exploratory semantic QC:
clustering, PCA, UMAP, k-means, pairwise distance), documented in
`supplementary/semantic_qc_research.md`, not here.

## `osteosarcoma_wgts` — the actual current ARACNe3 pipeline this data feeds

`analyses/aracne3_network_reconstruction/README.md` gives the concrete,
current-generation spec (ARACNe3, not the 2006 algorithm):

- Expression matrix: tab-delimited, genes as rows, samples as columns, first
  column named `Gene`.
- "Expression values should be normalized but not log-transformed."
- Recommended: **filtered non-log TMM-normalized CPM**. Acceptable
  alternative if raw counts aren't available: filtered non-log TPM.
- Explicitly avoid: raw counts, log2(CPM+1), log2(TPM+1), z-scored
  expression.
- "Lowly expressed genes should be filtered out before running ARACNe3."
  "Non-protein-coding genes should be removed if using a protein-coding gene
  universe."
- Two regulator lists (TF+coTF, signaling proteins), run as separate ARACNe3
  jobs then concatenated into one network for VIPER. Regulator ID type must
  match the expression matrix's gene ID convention.
- "For VIPER, use a normalized log-scale expression matrix, ideally: log2
  TMM-normalized CPM. The VIPER expression matrix should use the same sample
  set and compatible gene identifiers as the ARACNe3 network."

`resources/regulator_lists_for_aracne3/README.md`: regulator lists originate
from `califano-lab/NaRnEA` (Entrez ID based), then mapped to Ensembl and gene
symbol via `org.Hs.eg.db`. A separate `gene_symbol_gencode_v19/` variant
exists only because that lab's Salmon/Isabl pipeline uses GENCODE v19 — not
relevant here since the GDC STAR files used in this project are GENCODE v36.
The plain `gene_symbol/{tf_cotf_sym.txt,sig_sym.txt}` lists (not tied to any
GENCODE version) are the right match, using each STAR file's `gene_name`
column. "The final regulator list used in a specific ARACNe3 run should be
filtered to regulators present in that run's expression matrix."

## Original ARACNE algorithm paper (Margolin et al. 2006, BMC Bioinformatics)

Read in full (15 pages). This is a microarray-era methods paper, not a
software manual — it doesn't address RNA-seq normalization, file formats, or
TCGA-scale cohort mixing at all. What it does establish:

- MI estimation "copula-transform[s] (i.e., rank-order)" the data internally
  — "This decreases the influence of arbitrary transformations involved in
  microarray data preprocessing." This is the basis for ARACNe/VIPER's
  documented robustness to a shared, monotonic batch shift (relevant to the
  TCGA-LAML/Center-13 decision — see `lab_notebook.ipynb`, 2026-08-12 section).
- No gene-filtering or HVG-style preselection anywhere in the method —
  ARACNE is defined as scanning all regulator×target pairwise MI, then
  pruning indirect edges via DPI. Variance-based feature selection isn't
  part of how ARACNe works (see scope note above).
- No hard minimum sample size stated, but a synthetic benchmark (Table 1)
  shows performance "decays gracefully" down to ~125 samples, and their one
  real network was built from ~340 samples of a single, homogeneous cell
  population (B lymphocytes) — not a pooled multi-tissue cohort.

## Applied Califano-lab papers on real TCGA data

**Mundi et al. (OncoTarget/OncoTreat, Cancer Discov 2023,
`nihms-1885688.pdf`)** and **metaVIPER (`metaVIPER_paper.pdf`)**:

- Normalization used for their TCGA regulons: raw counts → DESeq2
  variance-stabilizing transformation (VST). This predates and differs from
  the `osteosarcoma_wgts` repo's more current TMM-CPM guidance above — the
  repo's guidance is what this pipeline follows, since it's the actual target
  pipeline, but VST is worth knowing as the precedent in the foundational
  papers.
- Networks built **per tumor type**, never pooled: "The networks were
  reverse engineered by ARACNe from ≥ 100 RNASeq profiles of human cancer
  tissue from... TCGA." metaVIPER assembled "Twenty-four core TCGA RNA-Seq
  derived interactomes," one per cohort.
- Gene filtering: not low-expression removal in the classic sense — both
  restrict ARACNe's *candidate regulators* to curated categories (~1,800-1,900
  TFs, ~700-1,000 cofactors, ~3,400-3,900 signaling genes; DPI=0, MI
  p=10⁻⁸). "Genes whose expression is not captured (quantified) in TCGA are
  excluded from the DGES" — a VIPER-signature filter, not an ARACNe-network
  filter.
- VIPER reference cohort — the two papers disagree in practice. Mundi et al.
  explicitly considered and rejected GTEx/matched-normal references
  ("would potentially over-emphasize proliferative and cell cycle signals...
  and under-emphasize lineage specific tumor vulnerabilities") and instead
  used **pan-TCGA tumor pool (11,289 samples)**, with each sample's signature
  computed as "the gene-wise relative expression to the distribution of that
  gene across [the pool]... expressed as its quantile relative to the
  reference model." OncoLoop (`nihms-1851760.pdf`), by contrast, used
  matched-tissue **GTEx normal prostate (n=245)** as its VIPER reference —
  its Supplementary Methods (not in this PDF) would have the exact
  statistical transform. This disagreement means the reference-cohort
  strategy for this project is a real open design choice, not something the
  literature settles — deferred to the VIPER-prep step.
- Batch effects: "due to VIPER's use of robust reporter sets to compute the
  activity of each protein, moderate biases in RNA profiles based on RNA
  extraction method, sequencing instrument, and reference transcriptome
  version used to map reads... generally have minimal effect on protein
  activity assessment." metaVIPER's whole design rationale is similar:
  regulon-based enrichment scoring is claimed to be inherently more
  batch-robust than raw expression, though neither paper applies a separate
  numerical batch-correction step (no ComBat, etc.) — the robustness claim is
  about the scoring method itself, not an added correction.

## VIPER paper/docs (`VIPER_paper.pdf`, `using_Viper.pdf`,
`viper_package_reference.pdf`, `VIPER_Dylan_Notes.pdf`)

- The original paper's own TCGA analysis: "raw counts were normalized to
  account for different library size, and the variance was stabilized by
  fitting the dispersion... as implemented in the DESeq R package."
- Signature-vs-reference-cohort computation is explicitly flexible:
  `viperSignature()` supports `method = c("zscore","ttest","mean")`; Online
  Methods describes "comparing the expression levels of each feature in a
  test sample against a set of reference samples by any suitable method,
  including... Student's t-test, Z-score transformation or fold change; or...
  the average expression level across all samples when clear reference
  samples are not available."
- The final enrichment step (aREA) is separately rank/quantile-normal based
  regardless of which GES method is chosen — this buffers against some
  normalization noise but doesn't make the upstream normalization choice
  irrelevant.
- No stated minimum reference-cohort size. No requirement that the
  ARACNe-building cohort and the VIPER reference cohort share identical
  normalization — `viper()`/`viperSignature()` take arbitrary expression
  matrices independent of how the regulon itself was built.
- `VIPER_Dylan_Notes.pdf` (internal MSKCC notes) shows a real pipeline
  supporting both a pooled `TCGA_TARGET` reference and disease-specific
  network+reference pairs via a `disease_map.tsv` — confirms both strategies
  are live options in practice at this lab, not just in the papers.

## Bottom line for this project's design decisions

See `lab_notebook.ipynb` (2026-08-13 section) for how these translate into
concrete choices: three separate normalized views (log2(TPM+1) for semantic
QC, non-log per-cohort TMM-CPM for ARACNe, log2 TMM-CPM for VIPER) derived
from one shared raw-counts base; no HVG selection anywhere near ARACNe;
gene-symbol matching to the `osteosarcoma_wgts` regulator lists; per-cohort
ARACNe networks with several TCGA/TARGET cohorts below the ~100-sample
practical floor flagged as an open problem, not solved here.
