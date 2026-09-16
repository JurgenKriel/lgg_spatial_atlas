#!/usr/bin/env python3
"""Build ONE cohort-wide palette from every centroids store.

WHY THIS EXISTS
Palettes are currently taken per-sample from that sample's own `uns` colours. If
sample A lacks a cell type that sample B has, a per-sample palette silently
shifts every subsequent colour — so the same cell type renders differently in
two samples, and a reader comparing them draws a false conclusion. That is a
correctness bug, not a cosmetic one. The fix is to fix the label -> colour map
once, over the UNION of labels across the whole cohort.

This also reports DISAGREEMENTS: where two stores assign different colours to
the same label, which is the bug above caught in the act.

Run with an environment that has zarr 2.x (spatialdata_env_2).

Usage:
    make_cohort_palette.py venture_ST/centroids --out palettes.json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

import zarr

# Not a biological niche — a placeholder that leaked into the annotations and
# appears across samples. It has no identity in the canonical niche key, so it
# must not reach a legend.
DROP_LABELS = {"white", "nan", "NA", ""}

FIELDS = (("Anno", "cell_type"), ("niche", "niche"))


def read_store(path: str) -> dict[str, dict[str, str]]:
    """label -> colour for each annotation field in one centroids store."""
    out: dict[str, dict[str, str]] = {}
    try:
        g = zarr.open(path, mode="r")
    except Exception as exc:  # a store emptied or half-written
        print(f"  ! {os.path.basename(path)}: cannot open ({exc})", file=sys.stderr)
        return out

    try:
        tbl = g["tables/cell_annotations"]
    except KeyError:
        print(f"  ! {os.path.basename(path)}: no tables/cell_annotations", file=sys.stderr)
        return out

    for src, dest in FIELDS:
        cats = colours = None
        try:
            cats = [str(c) for c in tbl[f"obs/{src}/categories"][:]]
        except Exception:
            continue
        # anndata writes the palette to uns/<field>_colors, positionally aligned
        # with the categories array.
        for key in (f"uns/{src}_colors", f"uns/{src}_color"):
            try:
                colours = [str(c) for c in tbl[key][:]]
                break
            except Exception:
                continue
        if colours is None or len(colours) != len(cats):
            continue
        out[dest] = {c: col for c, col in zip(cats, colours)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("centroids_dir")
    ap.add_argument("--out", default="palettes.json")
    args = ap.parse_args()

    stores = sorted(
        os.path.join(args.centroids_dir, d)
        for d in os.listdir(args.centroids_dir)
        if d.endswith("_centroids.zarr")
    )
    if not stores:
        raise SystemExit(f"no *_centroids.zarr under {args.centroids_dir}")
    print(f"reading {len(stores)} centroids stores", file=sys.stderr)

    seen: dict[str, dict[str, collections.Counter]] = {
        "cell_type": collections.defaultdict(collections.Counter),
        "niche": collections.defaultdict(collections.Counter),
    }
    contributing = 0
    for path in stores:
        got = read_store(path)
        if got:
            contributing += 1
        for field, mapping in got.items():
            for label, colour in mapping.items():
                if label in DROP_LABELS:
                    continue
                seen[field][label][colour] += 1

    palettes: dict[str, dict[str, str]] = {}
    conflicts = 0
    for field, labels in seen.items():
        out: dict[str, str] = {}
        for label in sorted(labels):
            counts = labels[label]
            colour, _ = counts.most_common(1)[0]
            out[label] = colour
            if len(counts) > 1:
                conflicts += 1
                others = ", ".join(f"{c}×{n}" for c, n in counts.most_common()[1:])
                print(f"  ! {field} '{label}': stores disagree — using {colour}, "
                      f"also saw {others}", file=sys.stderr)
        palettes[field] = out

    with open(args.out, "w") as fh:
        json.dump(palettes, fh, indent=2)
        fh.write("\n")

    print(f"\n{contributing}/{len(stores)} stores contributed", file=sys.stderr)
    for field, mapping in palettes.items():
        print(f"{field}: {len(mapping)} labels", file=sys.stderr)
    if conflicts:
        print(f"\n{conflicts} label(s) had conflicting colours across stores — "
              f"resolved by majority. This is exactly the bug a cohort-wide "
              f"palette exists to prevent.", file=sys.stderr)
    print(f"wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
