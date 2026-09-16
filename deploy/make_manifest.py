#!/usr/bin/env python3
"""Generate a release manifest for the Venture atlas (components D-3 / REQ-11).

The manifest is the ONLY place the cohort is enumerated. Nothing in the viewer,
the nginx config or the deploy scripts may carry a sample list; the UI is built
from this file. See .planning/phases/06-cohort/06-VIEWER-ARCHITECTURE.md.

SCHEMA 3 — two axes, because the cohort genuinely has two shapes
    The ven series are serial z-stacks of one block: the axis is DEPTH.
    The GL / GX / LGG patients are flat sections at different CLINICAL
    TIMEPOINTS (primary vs recurrent, split by treatment): the axis is TIME,
    and often a different specimen entirely. Presenting a recurrent tumour as
    "another z-plane" of the primary would be actively misleading, so a patient
    carries an `axis` and the viewer renders a depth slider or a timepoint
    selector accordingly.

Section identity comes from `build/make_sections_table.py`, which is also the
naming normaliser (the cohort CSV says `GX008`/`LGGA`; the stores say
`GX0008`/`LGG-A1`). Without that table this falls back to parsing `_z<N>` from
filenames, which is enough for the single-patient pilot.

Recognised filenames in a release directory:
    <prefix>-<section>-anndata.zarr        cells (genes / cell type / niche)
    ms_<section>-anndata.zarr              MS ion density
    <prefix>-<section>-config.json         the Vitessce config for that section

Usage:
    make_manifest.py <release-dir> <version> [--sections sections.csv]
                                             [--palettes palettes.json]
                                             [--niche-key build/niche_key.json]
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import re
import sys

Z_FALLBACK = re.compile(r"^(?P<patient>.+)_z(?P<z>\d+)$")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_NICHE_KEY = os.path.join(REPO, "build", "niche_key.json")


def load_sections(path: str | None) -> dict[str, dict]:
    if not path:
        return {}
    with open(path, newline="") as fh:
        return {r["section"]: r for r in csv.DictReader(fh)}


def split_name(name: str, known: set[str]) -> tuple[str | None, str | None]:
    """Return (kind, section) for a release filename.

    Section ids contain dots and hyphens (GL0043_1.1, GX0008-2, LGG-A1), so a
    greedy `<prefix>-<section>` regex is ambiguous. Match against the known
    section ids instead, longest first; fall back to the `_z<N>` convention when
    no sections table was supplied.
    """
    for kind, suffix in (("cells", "-anndata.zarr"), ("config", "-config.json")):
        if name.startswith("ms_"):
            continue
        if not name.endswith(suffix):
            continue
        stem = name[: -len(suffix)]
        for sec in sorted(known, key=len, reverse=True):
            if stem.endswith("-" + sec):
                return kind, sec
        m = re.search(r"-([A-Za-z0-9._-]+_z\d+)$", stem)
        if m:
            return kind, m.group(1)
    if name.startswith("ms_") and name.endswith("-anndata.zarr"):
        stem = name[len("ms_"): -len("-anndata.zarr")]
        if stem in known or Z_FALLBACK.match(stem):
            return "ms", stem
        for sec in sorted(known, key=len, reverse=True):
            if stem == sec:
                return "ms", sec
    return None, None


def _n_cells(release_dir: str, store: str) -> int | None:
    """Cell count from consolidated metadata, without opening arrays."""
    try:
        with open(os.path.join(release_dir, store, ".zmetadata")) as fh:
            meta = json.load(fh)["metadata"]
    except (OSError, KeyError, ValueError):
        return None
    for key in ("X/.zarray", "obs/_index/.zarray"):
        arr = meta.get(key)
        if arr and arr.get("shape"):
            return int(arr["shape"][0])
    return None


def _legend(palettes: dict | None, niche_key: dict | None) -> dict:
    """Cohort-wide legend: label -> colour, plus a biological identity for niches.

    Colours must come from a palette computed over the UNION of labels across
    all samples. A per-sample palette silently shifts colours when a sample
    lacks a category, so the same cell type renders differently in two samples
    and a reader comparing them draws a false conclusion.
    """
    out: dict = {}
    if not palettes:
        return out
    if "cell_type" in palettes:
        out["cell_type"] = dict(palettes["cell_type"])
    if "niche" in palettes:
        key = (niche_key or {}).get("niches", {})
        by_display = {v.get("display", k): v for k, v in key.items()}
        niche_out = {}
        for label, colour in palettes["niche"].items():
            entry = {"color": colour}
            info = key.get(label) or by_display.get(label) or key.get(label.replace("-", "_"))
            if info and info.get("identity"):
                entry["identity"] = info["identity"]
            niche_out[label] = entry
        out["niche"] = niche_out
    return out


def build(release_dir: str, version: str, sections: dict[str, dict],
          palettes: dict | None = None, niche_key: dict | None = None) -> dict:
    try:
        names = sorted(os.listdir(release_dir))
    except FileNotFoundError:
        raise SystemExit(f"release directory not found: {release_dir}")

    found: dict[str, dict] = {}
    for name in names:
        kind, sec = split_name(name, set(sections))
        if not kind:
            continue
        slot = found.setdefault(sec, {})
        slot[{"cells": "cells_zarr", "ms": "ms_zarr", "config": "config"}[kind]] = name

    incomplete = sorted(s for s, v in found.items() if "config" not in v)
    if incomplete:
        print(f"warning: no config, will be omitted: {', '.join(incomplete)}", file=sys.stderr)

    patients: dict[str, dict] = {}
    for sec in sorted(found):
        entry = found[sec]
        if "config" not in entry:
            continue
        meta = sections.get(sec, {})
        zm = Z_FALLBACK.match(sec)
        patient = meta.get("patient") or (zm.group("patient") if zm else sec)
        axis = meta.get("axis") or ("z" if zm else "timepoint")
        label = meta.get("label") or (f"z{int(zm.group('z'))}" if zm else sec)
        try:
            order = float(meta.get("order", ""))
        except ValueError:
            order = float(zm.group("z")) if zm else 0.0

        sect = {"id": sec, "label": label, "axis": axis, "order": order, **entry}
        if zm:
            sect["z"] = int(zm.group("z"))
        if meta.get("treatment"):
            sect["treatment"] = meta["treatment"]
        if entry.get("cells_zarr"):
            n = _n_cells(release_dir, entry["cells_zarr"])
            if n is not None:
                sect["n_cells"] = n

        p = patients.setdefault(patient, {"id": patient, "label": patient, "sections": []})
        if meta.get("grade"):
            p["grade"] = meta["grade"]
        p["sections"].append(sect)

    for p in patients.values():
        p["sections"].sort(key=lambda s: (s["order"], s["id"]))
        axes = {s["axis"] for s in p["sections"]}
        # ven5 legitimately has both: an 8-plane stack plus two later timepoints.
        p["axis"] = axes.pop() if len(axes) == 1 else "mixed"
        p["n_sections"] = len(p["sections"])
        mods = ["cells"] if any(s.get("cells_zarr") for s in p["sections"]) else []
        if any(s.get("ms_zarr") for s in p["sections"]):
            mods.append("ms")
        p["modalities"] = mods

    return {
        "schema": 3,
        "version": version,
        "generated": _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "cohort": "venture",
        "legend": _legend(palettes, niche_key),
        "patients": [patients[k] for k in sorted(patients)],
    }


def _load_json(path: str | None, what: str) -> dict | None:
    if not path:
        return None
    try:
        with open(path) as fh:
            return json.load(fh)
    except OSError as exc:
        print(f"warning: could not read {what} ({exc}); continuing without it", file=sys.stderr)
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("release_dir")
    ap.add_argument("version")
    ap.add_argument("--sections", help="sections.csv from build/make_sections_table.py")
    ap.add_argument("--palettes", help="cohort-wide palettes.json (union over all samples)")
    ap.add_argument("--niche-key", default=DEFAULT_NICHE_KEY)
    args = ap.parse_args()

    manifest = build(
        args.release_dir, args.version,
        sections=load_sections(args.sections),
        palettes=_load_json(args.palettes, "palettes"),
        niche_key=_load_json(args.niche_key, "niche key"),
    )
    json.dump(manifest, sys.stdout, indent=2)
    sys.stdout.write("\n")

    n_sec = sum(p["n_sections"] for p in manifest["patients"])
    n_ms = sum(1 for p in manifest["patients"] for s in p["sections"] if "ms_zarr" in s)
    print(f"{len(manifest['patients'])} patients, {n_sec} sections ({n_ms} with MS): "
          + ", ".join(f"{p['id']}[{p['axis']}×{p['n_sections']}]" for p in manifest["patients"]),
          file=sys.stderr)


if __name__ == "__main__":
    main()
