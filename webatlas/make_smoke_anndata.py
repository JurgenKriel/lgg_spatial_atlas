"""Tiny synthetic AnnData mirroring the atlas target layout (spatial centroids,
cell_type + niche categoricals, gene matrix X) to smoke-test webatlas-pipeline."""
import sys
import numpy as np, pandas as pd, anndata as ad
rng = np.random.default_rng(0)
n = 200
genes = [f"GENE{i}" for i in range(20)]
X = rng.poisson(3, size=(n, len(genes))).astype("float32")
obs = pd.DataFrame({
    "cell_type": pd.Categorical(rng.choice(["Tumor", "Immune", "Vascular"], n)),
    "niche":     pd.Categorical(rng.choice(["T-ROS", "T-PAN", "V"], n)),
}, index=[f"cell{i}" for i in range(n)])
adata = ad.AnnData(X=X, obs=obs, var=pd.DataFrame(index=genes), dtype="float32")
adata.obsm["spatial"] = (rng.random((n, 2)) * 1000).astype("float32")
adata.uns["cell_type_colors"] = ["#e41a1c", "#377eb8", "#4daf4a"]
adata.uns["niche_colors"] = ["#984ea3", "#ff7f00", "#a65628"]
out = sys.argv[1] if len(sys.argv) > 1 else "smoke_anndata.h5ad"
adata.write_h5ad(out)
print(f"wrote {out}: {adata.n_obs} cells x {adata.n_vars} genes; "
      f"obs={list(adata.obs.columns)}; obsm={list(adata.obsm.keys())}")
