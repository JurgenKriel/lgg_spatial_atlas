"""Build the native MS ion-density layer for the atlas: one AnnData of MS spots
(aligned frame) x m/z intensities, so a chosen m/z renders as an ion-density map
(matching scripts/ven6_IF_plot+transcripts+metabolites.ipynb)."""
import sys, os, numpy as np, pandas as pd, anndata as ad
from scipy.sparse import csr_matrix

SRC = sys.argv[1]                      # e.g. venture_pt2/aligned_metabolites/z1_met_final.txt
OUT = sys.argv[2]                      # output h5ad
ZNAME = sys.argv[3] if len(sys.argv) > 3 else "ven2_z1"

df = pd.read_csv(SRC, sep="\t")
coord_cols = ["x", "y", "transformed_x", "transformed_y", "transformed_x2", "transformed_y2"]
mz_cols = [c for c in df.columns if c.startswith("X")]
# transformed_x/y verified as the aligned frame (median NN dist to a cell ~13u)
xy = df[["transformed_x", "transformed_y"]].to_numpy(dtype="float32")

X = csr_matrix(df[mz_cols].to_numpy(dtype="float32"))
raw_mz = np.array([float(c[1:]) for c in mz_cols], dtype="float64")
var = pd.DataFrame({"raw_mz": raw_mz}, index=[f"mz-{v:.4f}" for v in raw_mz])
var["feature_type"] = "metabolite"
var["is_metabolite"] = True

obs = pd.DataFrame(index=[str(i) for i in range(len(df))])
obs["z_plane"] = ZNAME
a = ad.AnnData(X=X, obs=obs, var=var)
a.obsm["spatial"] = xy
os.makedirs(os.path.dirname(OUT), exist_ok=True)
a.write_h5ad(OUT)
print(f"wrote {OUT}: {a.n_obs} MS spots x {a.n_vars} m/z | "
      f"x {xy[:,0].min():.0f}-{xy[:,0].max():.0f} y {xy[:,1].min():.0f}-{xy[:,1].max():.0f}")
print("example m/z:", list(a.var_names[:3]))
