#!/usr/bin/env python3
"""Assemble one cohort section into a Vitessce-ready AnnData zarr.

Input is the per-section h5ad exported from the cohort SingleCellExperiment,
whose colData already carries cell type (`annotation`), `niche` and coordinates
(`x_coord`, `y_coord`) — so no join against the centroids stores is needed. A
centroids store can still be supplied to override or fill gaps.

Decisions baked in here, each with a reason:

  * **X is dense float32.** Dense because sparse CSR triggers Vitessce's
    `LoaderNotFoundError` — hard-won. float32 rather than the float64 the pilot
    shipped, because expression counts do not carry sixteen significant figures
    and it halves both the stored atlas and the bytes a reviewer pulls per
    interaction, which is metered off-net.
  * **`var/is_gene` is written here.** The config builder filters on it. In the
    pilot it existed only because a Nextflow step added it, so a build that
    skipped that step produced a store the viewer could not read.
  * **`obsp/` and `obsm/X_pca` are dropped.** The viewer never reads them; they
    were scanpy leftovers inflating every store.
  * **Colours come from the cohort palette**, never from this section's own
    categories — a per-section palette gives the same cell type different
    colours in different patients.

Usage:
    build_section_zarr.py --section ven2_z1 --h5ad ven2_z1.h5ad \
        --out venture_atlas-ven2_z1-anndata.zarr --palettes palettes.json
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

import anndata as ad
import numpy as np
import pandas as pd
import zarr

# Not a biological niche — a placeholder that leaked into the annotations. It
# has no identity in the canonical niche key and must not reach a legend.
DROP_NICHE = {"white", "nan", "NA", ""}

CELL_TYPE_KEYS = ("annotation", "Anno", "celltype", "cell_type", "annotation_cytospace")
NICHE_KEYS = ("niche",)
X_KEYS = ("x_coord", "x_centroid", "x")
Y_KEYS = ("y_coord", "y_centroid", "y")


def pick(obs: pd.DataFrame, names, what: str) -> str:
    for n in names:
        if n in obs.columns:
            return n
    raise SystemExit(f"none of {names} present for {what}; have: {list(obs.columns)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--section", required=True)
    ap.add_argument("--h5ad", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--palettes")
    ap.add_argument("--max-cells", type=int, default=0,
                    help="subsample above this many cells (0 = keep all)")
    args = ap.parse_args()

    print(f"== {args.section}")
    adata = ad.read_h5ad(args.h5ad)
    print(f"   input      : {adata.n_obs:,} cells x {adata.n_vars} genes")

    ct_key = pick(adata.obs, CELL_TYPE_KEYS, "cell type")
    ni_key = pick(adata.obs, NICHE_KEYS, "niche")
    x_key = pick(adata.obs, X_KEYS, "x coordinate")
    y_key = pick(adata.obs, Y_KEYS, "y coordinate")

    # Drop cells with no usable coordinate — they cannot be placed and would
    # otherwise pile up at the origin and read as a dense artefact.
    xs = pd.to_numeric(adata.obs[x_key], errors="coerce").to_numpy()
    ys = pd.to_numeric(adata.obs[y_key], errors="coerce").to_numpy()
    good = np.isfinite(xs) & np.isfinite(ys)
    if not good.all():
        print(f"   ! dropping {int((~good).sum()):,} cells with no coordinate")
        adata = adata[good].copy(); xs = xs[good]; ys = ys[good]

    if args.max_cells and adata.n_obs > args.max_cells:
        rng = np.random.default_rng(0)
        keep = np.sort(rng.choice(adata.n_obs, args.max_cells, replace=False))
        print(f"   ! subsampling {adata.n_obs:,} -> {args.max_cells:,}")
        adata = adata[keep].copy(); xs = xs[keep]; ys = ys[keep]

    # --- X: dense float32 (see docstring) ------------------------------------
    X = adata.X
    X = np.asarray(X.todense()) if hasattr(X, "todense") else np.asarray(X)
    X = np.ascontiguousarray(np.nan_to_num(X, nan=0.0), dtype=np.float32)

    # --- obs the viewer actually uses ----------------------------------------
    ct = adata.obs[ct_key].astype(str).to_numpy()
    ni = adata.obs[ni_key].astype(str).to_numpy()
    ni = np.array(["unassigned" if v in DROP_NICHE else v for v in ni], dtype=object)

    obs = pd.DataFrame(index=adata.obs_names.astype(str))
    obs["cell_type"] = pd.Categorical(ct)
    obs["niche"] = pd.Categorical(ni)
    obs["section"] = pd.Categorical([args.section] * len(obs))

    var = pd.DataFrame(index=adata.var_names.astype(str))
    var["feature_type"] = pd.Categorical(["gene"] * adata.n_vars)
    var["is_gene"] = np.ones(adata.n_vars, dtype=bool)

    out = ad.AnnData(X=X, obs=obs, var=var)
    out.obsm["spatial"] = np.column_stack([xs, ys]).astype(np.float32)

    # --- uns: cohort palette, aligned to this section's categories -----------
    if args.palettes:
        with open(args.palettes) as fh:
            pal = json.load(fh)
        for field, key in (("cell_type", "cell_type"), ("niche", "niche")):
            cats = list(out.obs[field].cat.categories)
            out.uns[f"{field}_colors"] = np.array(
                [pal.get(key, {}).get(c, "#888888") for c in cats], dtype=object)
            missing = [c for c in cats if c not in pal.get(key, {}) and c != "unassigned"]
            if missing:
                print(f"   ! {field} not in cohort palette: {missing}", file=sys.stderr)

    if os.path.exists(args.out):
        shutil.rmtree(args.out)
    out.write_zarr(args.out)

    # Consolidated metadata collapses thousands of per-array metadata requests
    # into one per store — it is why the pilot loads at all.
    zarr.consolidate_metadata(args.out)

    size = sum(os.path.getsize(os.path.join(r, f))
               for r, _, fs in os.walk(args.out) for f in fs)
    nfiles = sum(len(fs) for _, _, fs in os.walk(args.out))
    print(f"   wrote      : {out.n_obs:,} cells, {size/1e6:.0f} MB, {nfiles} objects")
    print(f"   cell types : {len(out.obs['cell_type'].cat.categories)}  "
          f"niches: {len(out.obs['niche'].cat.categories)}")


if __name__ == "__main__":
    main()
