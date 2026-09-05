#!/usr/bin/env python3
"""Lay out gdc-client's UUID-folder downloads as downloads/<Project ID>/<Sample ID>.<ext>.

gdc-client saves each file under downloads/<File ID>/<original filename>. This
walks gdc_sample_sheet.tsv, finds each file, and symlinks it into
organized/<Project ID>/<Sample ID>.<data-type-suffix>.

Usage:
    python3 organize_downloads.py \
        --sample-sheet gdc_sample_sheet.2026-08-06.tsv \
        --downloads downloads \
        --out organized
"""
import argparse
import csv
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-sheet", required=True, type=Path)
    ap.add_argument("--downloads", required=True, type=Path, help="gdc-client output dir (UUID subfolders)")
    ap.add_argument("--out", required=True, type=Path, help="destination root")
    args = ap.parse_args()

    missing = 0
    linked = 0
    with args.sample_sheet.open(newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            file_id = row["File ID"]
            file_name = row["File Name"]
            src = args.downloads / file_id / file_name
            if not src.exists():
                missing += 1
                continue

            # File names look like <uuid>.rna_seq.augmented_star_gene_counts.tsv;
            # keep everything after the first "." as the descriptive suffix.
            parts = file_name.split(".", 1)
            suffix = "." + parts[1] if len(parts) > 1 else Path(file_name).suffix

            dest_dir = args.out / row["Project ID"]
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{row['Sample ID']}{suffix}"

            if dest.exists() or dest.is_symlink():
                dest = dest_dir / f"{row['Sample ID']}.{file_id}{suffix}"

            dest.symlink_to(src.resolve())
            linked += 1

    print(f"linked/copied: {linked}", file=sys.stderr)
    if missing:
        print(f"missing (not yet downloaded): {missing}", file=sys.stderr)


if __name__ == "__main__":
    main()
