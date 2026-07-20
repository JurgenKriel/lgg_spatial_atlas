import glob, anndata as ad, numpy as np, pandas as pd
files = sorted(glob.glob("/vast/scratch/users/kriel.j/atlas_pt2/h5ad/pt2_ven2_z*.h5ad"))
assert files, "no h5ad found"
ok=True
for f in files:
    a = ad.read_h5ad(f)
    ft = a.var["feature_type"].value_counts().to_dict()
    checks = {
        "cell_type in obs": "cell_type" in a.obs,
        "niche in obs": "niche" in a.obs,
        "spatial in obsm": "spatial" in a.obsm and a.obsm["spatial"].shape[1]==2,
        "feature_type gene+metab": ft.get("gene",0)>0 and ft.get("metabolite",0)>0,
        "cell_type_colors": len(a.uns.get("cell_type_colors",[]))==len(a.obs["cell_type"].cat.categories),
        "niche_colors": len(a.uns.get("niche_colors",[]))==len(a.obs["niche"].cat.categories),
        "no NaN niche": (a.obs["niche"].astype(str)!="NA").all(),
        "finite spatial": np.isfinite(a.obsm["spatial"]).all(),
    }
    bad = [k for k,v in checks.items() if not v]
    status = "OK" if not bad else f"FAIL:{bad}"
    if bad: ok=False
    print(f"{f.split('/')[-1]}: {a.n_obs} cells, genes={ft.get('gene')}, metab={ft.get('metabolite')}, "
          f"celltypes={a.obs['cell_type'].nunique()}, niches={a.obs['niche'].nunique()} -> {status}")
print("ALL VALID" if ok else "VALIDATION FAILED")
