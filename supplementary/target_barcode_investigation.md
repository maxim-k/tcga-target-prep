# TARGET disease subcodes + resolving legacy sample-type codes 41/42/85

2026-08-10. Backs the `TARGET_DISEASE_SUBCODE` / `TARGET_LEGACY_SAMPLE_TYPE`
lookups in `scripts/build_sample_breakdown.py`, applied in `lab_notebook.ipynb`.

**Goal:** resolve the 76 TARGET-AML files whose Sample Type Code (41/42/85)
had no `Sample Type Definition`, and decode the TARGET disease subcode
(barcode field 2, for example the `20` in `TARGET-20-D84-...`) the way TCGA disease
codes are already decoded.

**What this note checked, and how much held up:**
- This investigation consulted a local report, `TARGET Barcode Format Breakdown.pdf`. Its
  barcode anatomy and its canonical 7-project TARGET disease-code table
  (10=ALL-P1, 20=AML, 30=NBL, 40=OS, 50=WT, 51=CCSK, 52=RT) match the
  disease-code table derived independently from this data. Its page-long narrative about what code 85
  specifically "likely" means (CRISPR-Cas9 lineage tracing, JAK1/JAK2
  dependency, a PDX passage number) reads as hedged speculation, not a sourced fact—it never actually resolved the code despite citing a real cBioPortal page
  that could have.
- `api.gdc.cancer.gov` is reachable (via a fetch tool, not via direct `curl`
  in this sandbox—DNS fails there). The live Data Dictionary API
  (`/v0/submission/_dictionary/sample`) currently lists 81 permissible
  *text* values for `sample_type`, no numeric-code mapping, and 41/42/85 match
  none of them. A GDC news post ("New TCGA and TARGET Properties and Sample
  Type Restructuring") confirms GDC decomposed the old single `sample_type`
  into four properties—Tissue Type, Tumor Descriptor, Specimen Type,
  Preservation Method, exactly the four sample-sheet columns here—and for
  these 76 files three of those four already read "Unknown." So this is a
  genuine gap upstream in GDC's own data, not a decoding failure on this side.
- cBioPortal's `aml_target_gdc` study (the PDF's own citation, verified real
  and public—TARGET-AML data re-ingested from GDC via NCI's Cancer Data
  Aggregator, Aug 2025) independently resolves this. Queried directly for 4 of
  the 76 affected files across all three codes—**all four resolve to
  `sampleType: "Primary Solid Tumor"`**, the same meaning as standard code
  `01`. (One file, an internal "mock2" xenograft-derived aliquot, wasn't
  present in cBioPortal's import at all, so cBioPortal's import didn't
  guarantee coverage of all 76—in practice it covered all of them.)
  cBioPortal's clinical record for the code-85 patient just says
  `PRIMARY_DIAGNOSIS: "Myeloid leukemia, NOS"`—nothing about
  CBFA2T3-GLIS2/JAK1/JAK2/CRISPR, so the PDF's elaborate narrative for that
  specific barcode is not corroborated by the actual clinical data.
- TARGET disease subcode, full empirical picture: `10`/`30`/`40`/`50`/`51`/`52`
  match the PDF's canonical table. `20` also appears under TARGET-ALL-P3 for
  cases prefixed `SJAML...`, and `15` under TARGET-ALL-P3 for cases prefixed
  `SJMPAL...` (St. Jude Mixed Phenotype Acute Leukemia)—real, named
  sub-cohorts identifiable from the case-ID prefix itself, not a guess. `00`
  (88 files, all Tissue Type = Normal, for example `TARGET-00-RO02722`) looks like a
  shared reference/normal-control bucket rather than a disease code, but isn't
  officially documented anywhere found—flagged as inferred. `21` (55 files,
  all AML/Tumor) is genuinely unresolved—cBioPortal's clinical data shows
  nothing that distinguishes it from `20` beyond the code itself.

Both lookups are commented with their actual source in
`scripts/build_sample_breakdown.py`, applied via `decode_target_extras()`.
The legacy sample-type fill keeps a `Sample Type Definition Source` column
(`"GDC official"` vs `"inferred (cBioPortal)"`) so the two are never silently
blended.
