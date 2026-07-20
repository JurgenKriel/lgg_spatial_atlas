"""Build MS ion-density layers (dense zarr) for given z-planes, validating that
transformed_x/y really is the aligned frame against that plane's cell centroids."""
import sys, os, shutil, json
import numpy as np, pandas as pd, anndata as ad, zarr
from scipy.spatial import cKDTree

PLANES = {
 "z2": "/vast/projects/BCRL_Multi_Omics/venture_pt2/aligned_metabolites/Ven2B_z2_transformed_metabolite_matrix_final.txt",
 "z3": "/vast/projects/BCRL_Multi_Omics/venture_pt2/aligned_metabolites/Ven2C_z3_tranformed_metabolites_coordinates_final.txt",
}
OUTDIR="/vast/scratch/users/kriel.j/atlas_pt2/zarr_ms"
for z, src in PLANES.items():
    df = pd.read_csv(src, sep="\t")
    mz_cols=[c for c in df.columns if c.startswith("X")]
    cells=ad.read_h5ad(f"/vast/scratch/users/kriel.j/atlas_pt2/h5ad/pt2_ven2_{z}.h5ad")
    tree=cKDTree(np.asarray(cells.obsm["spatial"],dtype=float))
    rng=np.random.default_rng(0); idx=rng.choice(len(df), size=min(20000,len(df)), replace=False)
    best=None
    for xc,yc in [("transformed_x","transformed_y"),("x","y")]:
        d,_=tree.query(df.iloc[idx][[xc,yc]].to_numpy(dtype=float), k=1)
        med, frac = float(np.median(d)), float((d<50).mean())
        print(f"  {z} {xc}/{yc}: median NN {med:.1f}u, within50u {frac:.3f}")
        if best is None or frac>best[2]: best=(xc,yc,frac)
    xc,yc,frac=best
    print(f"  {z} -> using {xc}/{yc} (within50u={frac:.3f})")
    X=np.ascontiguousarray(df[mz_cols].to_numpy(dtype="float32"))
    raw=np.array([float(c[1:]) for c in mz_cols])
    var=pd.DataFrame({"raw_mz":raw}, index=[f"mz-{v:.4f}" for v in raw])
    var["feature_type"]="metabolite"; var["is_metabolite"]=True
    a=ad.AnnData(X=X, obs=pd.DataFrame(index=[str(i) for i in range(len(df))]), var=var)
    a.obsm["spatial"]=df[[xc,yc]].to_numpy(dtype="float32")
    out=f"{OUTDIR}/ms_ven2_{z}-anndata.zarr"
    if os.path.exists(out): shutil.rmtree(out)
    a.write_zarr(out, chunks=(4096, a.n_vars)); zarr.consolidate_metadata(out)
    print(f"  {z}: {a.n_obs} spots x {a.n_vars} m/z -> {out}")
