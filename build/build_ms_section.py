#!/usr/bin/env python3
"""Build the MS ion-density layer for one section.

Supersedes `build_ms_spots_anndata.py`, which asserted a single spelling
(`transformed_x`/`transformed_y`) and tab separation. The files it was written
for are not the ones `aligned_metabolites/` actually contains: those are
comma-separated with `x_transformed`/`y_transformed`. Rather than encode a
second set of assumptions, sniff both.

THE COORDINATE COLUMN IS THE WHOLE POINT
These tables carry raw `x`,`y` AND an aligned pair. The raw pair is in MS pixel
space and is NOT registered to the transcriptomics frame; using it silently
puts every metabolite in the wrong place, and the result still renders, which is
how it goes unnoticed. The aligned pair is preferred, and when cells are
supplied the choice is checked against them by nearest-neighbour distance
rather than trusted.

Usage:
    build_ms_section.py --section ven2_z4 --src <aligned.csv> \
        --out ms_ven2_z4-anndata.zarr [--cells <cells.zarr>]
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import sys

import anndata as ad
import numpy as np
import pandas as pd
import zarr

# Preference order: aligned spellings first, raw x/y only as a last resort.
COORD_CANDIDATES = (
    ("x_transformed", "y_transformed"),
    ("transformed_x", "transformed_y"),
    ("x_aligned", "y_aligned"),
    ("x", "y"),
)
MZ_RE = re.compile(r"^X?\d+\.?\d*$")


def sniff_sep(path: str) -> str:
    with open(path) as fh:
        head = fh.readline()
    try:
        return csv.Sniffer().sniff(head, delimiters=",\t;").delimiter
    except csv.Error:
        return "\t" if head.count("\t") > head.count(",") else ","


def nn_distance(spots: np.ndarray, cells: np.ndarray, n: int = 20000) -> float:
    """Median nearest-neighbour distance from spots to cells.

    Cheap sanity check on the coordinate choice: aligned coordinates sit on the
    tissue, unaligned ones sit somewhere else entirely, and the difference is
    orders of magnitude, not percent.
    """
    rng = np.random.default_rng(0)
    s = spots[rng.choice(len(spots), min(n, len(spots)), replace=False)]
    c = cells[rng.choice(len(cells), min(n, len(cells)), replace=False)]
    out = np.empty(len(s))
    for i in range(0, len(s), 2000):
        blk = s[i:i + 2000]
        d = np.sqrt(((blk[:, None, :] - c[None, :, :]) ** 2).sum(-1))
        out[i:i + len(blk)] = d.min(1)
    return float(np.median(out))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--section", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cells", help="cells zarr, to validate the coordinate choice")
    ap.add_argument("--max-nn", type=float, default=100.0,
                    help="fail if median NN distance to cells exceeds this (microns)")
    args = ap.parse_args()

    sep = sniff_sep(args.src)
    print(f"== {args.section}  (separator {sep!r})")
    df = pd.read_csv(args.src, sep=sep, low_memory=False)
    print(f"   input      : {len(df):,} spots x {df.shape[1]} columns")

    pair = next((p for p in COORD_CANDIDATES
                 if p[0] in df.columns and p[1] in df.columns), None)
    if pair is None:
        raise SystemExit(f"no coordinate pair found; columns start: {list(df.columns)[:8]}")
    if pair == ("x", "y"):
        print("   ! only RAW x/y present — these are MS pixel coordinates, not "
              "registered to the transcriptomics frame", file=sys.stderr)
    print(f"   coordinates: {pair[0]}, {pair[1]}")

    mz_cols = [c for c in df.columns
               if c not in {"x", "y", "is_edge", pair[0], pair[1]} and MZ_RE.match(str(c))]
    if not mz_cols:
        raise SystemExit("no m/z columns matched; expected bare floats or X-prefixed floats")
    print(f"   m/z features: {len(mz_cols)}")

    xy = df[list(pair)].to_numpy(dtype=np.float32)
    good = np.isfinite(xy).all(1)
    if not good.all():
        print(f"   ! dropping {int((~good).sum()):,} spots with no coordinate")
        df, xy = df[good], xy[good]

    if args.cells:
        try:
            cz = zarr.open(args.cells, mode="r")
            cells_xy = np.asarray(cz["obsm/spatial"][:], dtype=np.float32)
            med = nn_distance(xy, cells_xy)
            print(f"   NN to cells: median {med:.1f} um")
            if med > args.max_nn:
                raise SystemExit(
                    f"median nearest-neighbour distance {med:.1f} um exceeds "
                    f"{args.max_nn} um — these coordinates are not aligned to the "
                    f"cells, so the layer would be spatially wrong")
        except SystemExit:
            raise
        except Exception as exc:
            print(f"   ! could not validate against cells ({exc})", file=sys.stderr)

    X = np.ascontiguousarray(
        np.nan_to_num(df[mz_cols].to_numpy(dtype=np.float32), nan=0.0))

    var = pd.DataFrame(index=pd.Index([str(c) for c in mz_cols]))
    var["feature_type"] = pd.Categorical(["metabolite"] * len(mz_cols))
    var["is_metabolite"] = np.ones(len(mz_cols), dtype=bool)

    obs = pd.DataFrame(index=pd.Index([f"{args.section}_spot:{i}" for i in range(len(df))]))
    obs["section"] = pd.Categorical([args.section] * len(df))

    out = ad.AnnData(X=X, obs=obs, var=var)
    out.obsm["spatial"] = xy

    if os.path.exists(args.out):
        shutil.rmtree(args.out)
    out.write_zarr(args.out)
    zarr.consolidate_metadata(args.out)

    size = sum(os.path.getsize(os.path.join(r, f))
               for r, _, fs in os.walk(args.out) for f in fs)
    print(f"   wrote      : {out.n_obs:,} spots, {size/1e6:.0f} MB")


if __name__ == "__main__":
    main()
