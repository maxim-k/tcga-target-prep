#!/usr/bin/env python3
"""Decode gdc_sample_sheet.tsv barcodes against tcga_code_tables and write a
multi-sheet breakdown spreadsheet (pivot counts by disease and sample type).

Sample Type codes (position 3 of the barcode, e.g. "01" in "-01A") are a
GDC-wide convention shared by TCGA and TARGET, so they decode for both.

Usage:
    python3 build_sample_breakdown.py \
        --sample-sheet gdc_sample_sheet.2026-08-06.tsv \
        --code-tables tcga_code_tables \
        --out sample_breakdown.xlsx
"""
import argparse
from pathlib import Path

import pandas as pd

# TARGET has no equivalent of tcga_code_tables/diseaseStudy.tsv, so this maps
# TARGET-<abbreviation> project IDs to full names by hand. Source: NCI TARGET
# "Cancers Selected for Study" (https://www.cancer.gov/ccg/research/genome-sequencing/target).
TARGET_DISEASE = {
    "AML": "Acute Myeloid Leukemia",
    "ALL-P1": "Acute Lymphoblastic Leukemia (Phase 1)",
    "ALL-P2": "Acute Lymphoblastic Leukemia (Phase 2)",
    "ALL-P3": "Acute Lymphoblastic Leukemia (Phase 3)",
    "NBL": "Neuroblastoma",
    "WT": "Wilms Tumor",
    "OS": "Osteosarcoma",
    "RT": "Rhabdoid Tumor",
    "CCSK": "Clear Cell Sarcoma of the Kidney",
}

# TARGET disease subcode = barcode field 2 (e.g. "20" in "TARGET-20-D84-...").
# No official GDC table for this either; derived empirically from
# sample_metadata.parquet cross-referenced against case-ID prefixes. "00" and
# "21" are inferred, not officially documented -- flagged as such rather than
# stated as fact.
TARGET_DISEASE_SUBCODE = {
    "10": "Acute Lymphoblastic Leukemia (Phase 1)",
    "15": "Mixed Phenotype Acute Leukemia (St. Jude, TARGET-ALL-P3 sub-cohort, case IDs prefixed SJMPAL)",
    "20": "Acute Myeloid Leukemia",
    "21": "Acute Myeloid Leukemia (distinct sub-cohort, exact meaning unresolved)",
    "30": "Neuroblastoma",
    "40": "Osteosarcoma",
    "50": "Wilms Tumor",
    "51": "Clear Cell Sarcoma of the Kidney",
    "52": "Rhabdoid Tumor",
    "00": "Reference/normal-control samples, not disease-specific (inferred: all Tissue Type = Normal, case IDs like TARGET-00-RO02722)",
}

# Sample Type codes 41/42/85 appear only in TARGET-AML and aren't in
# tcga_code_tables/sampleType.tsv or GDC's official sample_type dictionary.
# Resolved by cross-checking cBioPortal's aml_target_gdc study (an independent
# harmonization of the same GDC data via NCI's Cancer Data Aggregator), which
# resolves all sampled examples of these codes to "Primary Solid Tumor".
TARGET_LEGACY_SAMPLE_TYPE = {
    "41": "Primary Solid Tumor",
    "42": "Primary Solid Tumor",
    "85": "Primary Solid Tumor",
}

# Disease-group panel for the semantic-QC small-multiples grid, keyed by
# Project ID. Manually curated against OncoTree's tissue taxonomy
# (oncotree.mskcc.org/api/tumorTypes) -- NOT raw code-to-code matching,
# which is unsafe: OncoTree's own code "TGCT" means Tenosynovial Giant Cell
# Tumor (soft tissue), unrelated to TCGA's TGCT (Testicular Germ Cell
# Tumors, see tcga_code_tables/diseaseStudy.tsv). Each code below was
# checked against its verified full disease name, not matched by string.
# "Pan-GI"/"Pan-Gyn"/"Genitourinary"/"Endocrine"/"Melanoma" are standard
# clinical/genomics groupings merging adjacent OncoTree tissues, labeled as
# such rather than presented as literal OncoTree categories. "Other solid"
# is an honest catch-all for sites with no natural partner among these 42
# codes, not a fake coherent label.
ONCOTREE_GROUP = {
    # Kidney (OncoTree tissue: Kidney)
    "TCGA-KIRC": "Kidney", "TCGA-KIRP": "Kidney", "TCGA-KICH": "Kidney",
    "TARGET-WT": "Kidney", "TARGET-RT": "Kidney", "TARGET-CCSK": "Kidney",
    # Myeloid leukemia (OncoTree tissue: Myeloid)
    "TCGA-LAML": "Myeloid leukemia", "TARGET-AML": "Myeloid leukemia",
    # Lymphoid leukemia/lymphoma (OncoTree tissue: Lymphoid)
    "TARGET-ALL-P1": "Lymphoid leukemia/lymphoma", "TARGET-ALL-P2": "Lymphoid leukemia/lymphoma",
    "TARGET-ALL-P3": "Lymphoid leukemia/lymphoma", "TCGA-DLBC": "Lymphoid leukemia/lymphoma",
    # CNS/Brain
    "TCGA-LGG": "CNS/Brain", "TCGA-GBM": "CNS/Brain",
    # Lung
    "TCGA-LUAD": "Lung", "TCGA-LUSC": "Lung",
    # Pan-GI (Bowel, Esophagus/Stomach, Liver, Biliary Tract, Pancreas)
    "TCGA-COAD": "Pan-GI", "TCGA-READ": "Pan-GI", "TCGA-STAD": "Pan-GI",
    "TCGA-ESCA": "Pan-GI", "TCGA-LIHC": "Pan-GI", "TCGA-CHOL": "Pan-GI", "TCGA-PAAD": "Pan-GI",
    # Pan-Gyn (Ovary/Fallopian Tube, Uterus, Cervix)
    "TCGA-OV": "Pan-Gyn", "TCGA-UCEC": "Pan-Gyn", "TCGA-UCS": "Pan-Gyn", "TCGA-CESC": "Pan-Gyn",
    # Genitourinary, non-kidney (Bladder/Urinary Tract, Prostate, Testis)
    "TCGA-BLCA": "Genitourinary", "TCGA-PRAD": "Genitourinary", "TCGA-TGCT": "Genitourinary",
    # Endocrine (Thyroid, Adrenal Gland)
    "TCGA-THCA": "Endocrine", "TCGA-ACC": "Endocrine", "TCGA-PCPG": "Endocrine",
    # Melanoma (Skin, Eye)
    "TCGA-SKCM": "Melanoma", "TCGA-UVM": "Melanoma",
    # Breast
    "TCGA-BRCA": "Breast",
    # Other solid (Soft Tissue, Bone, Peripheral Nervous System, Pleura, Head and Neck, Thymus)
    "TCGA-SARC": "Other solid", "TARGET-OS": "Other solid", "TARGET-NBL": "Other solid",
    "TCGA-MESO": "Other solid", "TCGA-HNSC": "Other solid", "TCGA-THYM": "Other solid",
}


def load_code_table(path: Path, key_col: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t", dtype=str)
    return df.set_index(key_col)


def decode_core_columns(sheet: pd.DataFrame, code_tables: Path) -> pd.DataFrame:
    """Add Sample Type Code/Definition and Disease columns to a gdc_sample_sheet frame."""
    sample_type = load_code_table(code_tables / "sampleType.tsv", "Code")
    disease = load_code_table(code_tables / "diseaseStudy.tsv", "Study Abbreviation")

    # Barcodes normally have 4 hyphen-separated fields, but some TARGET case
    # IDs embed extra descriptive tokens (e.g. "TARGET-20-PAYKSD-Unsorted-09A"),
    # so the sample-type+vial code must be read from the *last* token, not a
    # fixed index.
    sheet["Sample Type Code"] = sheet["Sample ID"].str.split("-").str[-1].str[:2]

    is_tcga = sheet["Project ID"].str.startswith("TCGA-")

    sheet["Disease"] = sheet["Project ID"].str.removeprefix("TCGA-").map(disease["Study Name"])
    sheet.loc[~is_tcga, "Disease"] = sheet.loc[~is_tcga, "Project ID"].str.removeprefix("TARGET-").map(TARGET_DISEASE)

    sheet["Sample Type Definition"] = sheet["Sample Type Code"].map(sample_type["Definition"])
    return sheet


def decode_target_extras(sheet: pd.DataFrame) -> pd.DataFrame:
    """Fill in TARGET-only gaps left by decode_core_columns: disease subcode
    names and the legacy (non-official) 41/42/85 sample-type codes. Requires
    a "TARGET Disease Subcode" column (see lab_notebook.ipynb)."""
    sheet["TARGET Disease Subcode Name"] = sheet["TARGET Disease Subcode"].map(TARGET_DISEASE_SUBCODE)

    sheet["Sample Type Definition Source"] = pd.NA
    sheet.loc[sheet["Sample Type Definition"].notna(), "Sample Type Definition Source"] = "GDC official"

    legacy = sheet["Sample Type Code"].map(TARGET_LEGACY_SAMPLE_TYPE)
    still_blank = sheet["Sample Type Definition"].isna()
    sheet.loc[still_blank, "Sample Type Definition"] = legacy[still_blank]
    sheet.loc[still_blank & legacy.notna(), "Sample Type Definition Source"] = "inferred (cBioPortal)"

    return sheet


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-sheet", required=True, type=Path)
    ap.add_argument("--code-tables", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    sheet = pd.read_csv(args.sample_sheet, sep="\t", dtype=str)
    sheet = decode_core_columns(sheet, args.code_tables)
    is_tcga = sheet["Project ID"].str.startswith("TCGA-")

    def by_disease_sorted(rows):
        return rows.groupby(["Project ID", "Disease"], dropna=False).size() \
            .reset_index(name="File Count").sort_values("File Count", ascending=False)

    by_disease_tcga = by_disease_sorted(sheet[is_tcga])
    by_disease_target = by_disease_sorted(sheet[~is_tcga])
    by_sample_type = sheet.groupby(["Sample Type Code", "Sample Type Definition"], dropna=False).size() \
        .reset_index(name="File Count").sort_values("File Count", ascending=False)
    disease_x_sampletype = pd.crosstab(sheet["Disease"], sheet["Sample Type Definition"]).replace(0, "")

    with pd.ExcelWriter(args.out, engine="openpyxl") as writer:
        by_disease_tcga.to_excel(writer, sheet_name="By Disease (TCGA)", index=False)
        by_disease_target.to_excel(writer, sheet_name="By Disease (TARGET)", index=False)
        by_sample_type.to_excel(writer, sheet_name="By Sample Type", index=False)
        disease_x_sampletype.to_excel(writer, sheet_name="Disease x Sample Type")

    print(f"wrote {args.out} ({len(sheet)} rows)")


if __name__ == "__main__":
    main()
