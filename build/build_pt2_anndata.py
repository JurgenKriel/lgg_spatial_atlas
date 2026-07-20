"""Assemble per-z-plane pt2 AnnData (h5ad) for the webatlas pipeline.
X = [SPT genes | SPM metabolites] with var['feature_type']; obs.cell_type (Anno) +
obs.niche (joined from cohort CSV); obsm['spatial'] = centroids; uns palettes."""
import os, json
import numpy as np, pandas as pd, anndata as ad
from scipy.io import mmread
from scipy.sparse import hstack, csr_matrix

MAT = "/vast/scratch/users/kriel.j/atlas_pt2/matrices"
OUT = "/vast/scratch/users/kriel.j/atlas_pt2/h5ad"; os.makedirs(OUT, exist_ok=True)
COH = "/vast/scratch/users/kriel.j/atlas_pt2/cohort_ven2.csv"

# integrated sample_id -> ven2 z-plane (from JOIN_KEY.md, 100% verified)
SAMPLE_MAP = {"6901_2":"ven2_z1","6901_1":"ven2_z2","6889_2":"ven2_z3","6889_1":"ven2_z4",
              "6694_2":"ven2_z5","6694_1":"ven2_z6","6687_2":"ven2_z7","6687_1":"ven2_z8"}

genes = [l.strip() for l in open(f"{MAT}/SPT_genes.txt")]
mets  = [l.strip() for l in open(f"{MAT}/SPM_metabolites.txt")]
coh = pd.read_csv(COH)  # niche source
coh_key = coh.set_index(["sample","cell_id"])

# palettes from the populated ven2 centroids zarr uns
def load_palettes():
    try:
        a = ad.read_zarr("/vast/scratch/users/kriel.j/centroids_2/ven2_centroids.zarr/tables/cell_annotations")
        ct = {c: col for c, col in zip(a.obs["Anno"].astype(str), a.obs["Anno_color"].astype(str))}
        ni = {c: col for c, col in zip(a.obs["niche"].astype(str), a.obs["niche_color"].astype(str))}
        return ct, ni
    except Exception as e:
        print("palette load failed:", e); return {}, {}
CT_PAL, NI_PAL = load_palettes()

summary = []
for sid, zname in SAMPLE_MAP.items():
    spt = mmread(f"{MAT}/{sid}_SPT.mtx").tocsr().T   # cells x genes
    spm = mmread(f"{MAT}/{sid}_SPM.mtx").tocsr().T   # cells x metabolites
    obs = pd.read_csv(f"{MAT}/{sid}_obs.csv")
    assert spt.shape[0] == spm.shape[0] == len(obs), (sid, spt.shape, spm.shape, len(obs))
    X = hstack([spt, spm]).tocsr()
    var = pd.DataFrame(index=genes + mets)
    var["feature_type"] = ["gene"]*len(genes) + ["metabolite"]*len(mets)

    # join niche via (zname, cell_id)
    idx = list(zip([zname]*len(obs), obs["cell_id"].astype(str)))
    niche = coh_key["niche"].reindex(idx).values
    obs = obs.copy()
    obs["niche"] = pd.Categorical(pd.Series(niche).fillna("NA").values)
    obs["cell_type"] = pd.Categorical(obs["Anno"].astype(str).values)
    obs["z_plane"] = zname
    obs.index = [f"{sid}_{b}" for b in obs["cell_id"].astype(str)]

    A = ad.AnnData(X=X, obs=obs[["cell_type","niche","cell_id","z_plane","x_centroid","y_centroid"]], var=var)
    A.obsm["spatial"] = obs[["x_centroid","y_centroid"]].to_numpy(dtype="float32")
    if {"x_aligned","y_aligned"}.issubset(obs.columns):
        A.obsm["spatial_aligned"] = obs[["x_aligned","y_aligned"]].to_numpy(dtype="float32")
    # palettes
    cats_ct = list(A.obs["cell_type"].cat.categories)
    cats_ni = list(A.obs["niche"].cat.categories)
    A.uns["cell_type_colors"] = [CT_PAL.get(c, "#888888") for c in cats_ct]
    A.uns["niche_colors"]     = [NI_PAL.get(c, "#888888") for c in cats_ni]

    matched = int(pd.notna(niche).sum())
    f = f"{OUT}/pt2_{zname}.h5ad"; A.write_h5ad(f)
    summary.append(dict(sample=sid, z=zname, cells=A.n_obs, genes=len(genes),
                        metabolites=len(mets), niche_matched=matched,
                        niche_frac=round(matched/A.n_obs, 4), file=f))
    print(f"  {zname}: {A.n_obs} cells x {A.n_vars} feats (gene+metab); niche {matched}/{A.n_obs}")

pd.DataFrame(summary).to_csv(f"{OUT}/build_summary.csv", index=False)
print("BUILD DONE ->", OUT)
