"""Build a Vitessce config that renders pt2 cells as a scatterplot of their spatial
coordinates (reliable points rendering, no raster needed) + UMAP, cell sets, feature list."""
import sys, json
from vitessce import VitessceConfig, ViewType as vt, AnnDataWrapper, Component as cm

Z_URL = sys.argv[1]   # full https URL to the -anndata.zarr
OUT   = sys.argv[2]   # output config path
NAME  = sys.argv[3] if len(sys.argv)>3 else "LGG pt2"

vc = VitessceConfig(schema_version="1.0.16", name=NAME)
w = AnnDataWrapper(
    adata_url=Z_URL,
    obs_embedding_paths=["obsm/spatial", "obsm/X_umap"],
    obs_embedding_names=["Spatial", "UMAP"],
    obs_embedding_dims=[[0, 1], [0, 1]],
    obs_set_paths=["obs/cell_type", "obs/niche"],
    obs_set_names=["Cell Type", "Niche"],
    obs_feature_matrix_path="X",
    coordination_values={"obsType": "cell", "featureType": "feature", "featureValueType": "expression"},
)
ds = vc.add_dataset(name="ven2_z1").add_object(w)
spatial = vc.add_view(vt.SCATTERPLOT, dataset=ds, mapping="Spatial")
umap    = vc.add_view(vt.SCATTERPLOT, dataset=ds, mapping="UMAP")
osets   = vc.add_view(vt.OBS_SETS, dataset=ds)
flist   = vc.add_view(vt.FEATURE_LIST, dataset=ds)
# layout: spatial big left; umap + sets + features stacked right
vc.layout((spatial | (umap / (osets / flist))))
cfg = vc.to_dict()
json.dump(cfg, open(OUT, "w"), indent=2)
print("wrote", OUT)
print("views:", sorted({v["component"] for v in cfg["layout"]}))
print("embeddings wired:", [f.get("options",{}).get("obsEmbedding") for d in cfg["datasets"] for f in d["files"]])
