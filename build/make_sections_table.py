#!/usr/bin/env python3
"""Derive the cohort section table from the cohort annotations CSV.

WHY THIS EXISTS
The cohort has two genuinely different data shapes and the atlas must not
pretend otherwise:

  * the **ven series** are true serial z-stacks of one tissue block
    (ven2/3/4/6 have 8 planes, ven1 has 2) — the axis is DEPTH;
  * the **GL / GX / LGG patients** are flat 2D sections where the extra
    sections are different CLINICAL TIMEPOINTS (primary vs recurrent, split by
    treatment) — the axis is TIME, and in several cases a different specimen
    entirely.

`export_centroids_to_spatialdata.py` collapses the second group by filling
`z_layer = "z0"` for any sample name not matching `_z<N>$`, which throws the
distinction away and would have the viewer present a recurrent-tumour specimen
as "another z-plane" of the primary. This script recovers it, and is also the
naming normaliser the cohort build needs (CSV `patient` values like `GX008` and
`LGGA` do not match on-disk forms `GX0008` and `LGG-A1`).

Output columns:
    section     the atlas unit, matching the centroids store / filename stem
    patient     grouping key, normalised
    axis        "z" (serial depth) or "timepoint" (clinical series)
    order       sort key within the patient
    label       what the viewer shows
    treatment   raw treatment value, for the label and for provenance
    n_cells     rows in the annotations CSV for this section

Usage:
    make_sections_table.py venture_ST/full_ven_cohort_annotations.csv > sections.csv
"""
from __future__ import annotations

import argparse
import collections
import csv
import re
import sys

Z_RE = re.compile(r"^(?P<patient>.+)_z(?P<z>\d+)$")

# Human labels for the treatment codes seen in the cohort CSV.
TREATMENT_LABEL = {
    "primary": "Primary",
    "recurrent_nil": "Recurrent (no adjuvant)",
    "recurrent_safu": "Recurrent (SAFU)",
    "recurrent_rt": "Recurrent (RT)",
    "recurrent_tmz_bev": "Recurrent (TMZ + bevacizumab)",
    "recurrent_tmz_rt": "Recurrent (TMZ + RT)",
    "recurrent_vora": "Recurrent (vorasidenib)",
}


def normalise_patient(patient: str, section: str) -> str:
    """Prefer the on-disk/section spelling over the CSV's `patient` spelling.

    The CSV says `GX008` and `LGGA`; the stores say `GX0008` and `LGG-A1`. The
    section string is what filenames are built from, so derive the group from it
    where the two disagree, and keep the CSV value only as a fallback.
    """
    m = re.match(r"^(GX\d+)", section)
    if m:
        return m.group(1)
    m = re.match(r"^(LGG-[A-Z])", section)
    if m:
        return m.group(1)
    m = re.match(r"^(GL\d+)", section)
    if m:
        return m.group(1)
    m = Z_RE.match(section)
    if m:
        return m.group("patient")
    # ven5.2.1 style: strip the trailing dotted section index
    m = re.match(r"^(ven\d+)", section)
    if m:
        return m.group(1)
    return patient


def sort_key(section: str, positioning: str, treatment: str) -> float:
    """Order sections within a patient.

    For a z-stack the plane number is the order. For a clinical series it is
    NOT the CSV's `positioning` column — those values (1.5, 2.0, 19.5, 20.0…)
    do not encode time, and sorting by them puts GL0043's recurrent section
    ahead of its three primaries. Order by primary-then-recurrent instead, which
    is the only ordering a reader would expect.
    """
    m = Z_RE.match(section)
    if m:
        return float(m.group("z"))
    return 0.0 if treatment == "primary" else 1.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("annotations_csv")
    ap.add_argument("--out", default="-")
    args = ap.parse_args()

    # Stream: the cohort CSV is ~790 MB / 7.1M rows. Never load it whole.
    counts: dict[str, int] = collections.Counter()
    meta: dict[str, dict] = {}

    with open(args.annotations_csv, newline="") as fh:
        reader = csv.DictReader(fh)
        for col in ("sample", "patient"):
            if col not in (reader.fieldnames or []):
                raise SystemExit(f"expected column '{col}' in {args.annotations_csv}; "
                                 f"found {reader.fieldnames}")
        for row in reader:
            section = row["sample"]
            counts[section] += 1
            if section not in meta:
                meta[section] = {
                    "patient_csv": row.get("patient", ""),
                    "treatment": row.get("treatment", "") or "",
                    "positioning": row.get("positioning", "") or "",
                    "grade": row.get("grade", "") or "",
                }

    rows = []
    for section, m in meta.items():
        patient = normalise_patient(m["patient_csv"], section)
        zm = Z_RE.match(section)
        axis = "z" if zm else "timepoint"
        if zm:
            label = f"z{int(zm.group('z'))}"
        else:
            label = TREATMENT_LABEL.get(m["treatment"], m["treatment"] or section)
        rows.append({
            "section": section,
            "patient": patient,
            "axis": axis,
            "order": sort_key(section, m["positioning"], m["treatment"]),
            "label": label,
            "treatment": m["treatment"],
            "grade": m["grade"],
            "n_cells": counts[section],
        })

    # A patient whose sections are all timepoints but which has several sections
    # sharing one treatment needs those disambiguated, or the selector shows
    # duplicate entries.
    by_patient_label = collections.Counter((r["patient"], r["label"]) for r in rows)
    for r in rows:
        if by_patient_label[(r["patient"], r["label"])] > 1:
            r["label"] = f"{r['label']} — {r['section']}"

    rows.sort(key=lambda r: (r["patient"], r["order"], r["section"]))

    out = sys.stdout if args.out == "-" else open(args.out, "w", newline="")
    w = csv.DictWriter(out, fieldnames=[
        "section", "patient", "axis", "order", "label", "treatment", "grade", "n_cells"])
    w.writeheader()
    w.writerows(rows)
    if out is not sys.stdout:
        out.close()

    patients = sorted({r["patient"] for r in rows})
    z_pat = sorted({r["patient"] for r in rows if r["axis"] == "z"})
    print(f"{len(rows)} sections across {len(patients)} patients "
          f"({len(z_pat)} with a z-stack: {', '.join(z_pat)})", file=sys.stderr)


if __name__ == "__main__":
    main()
