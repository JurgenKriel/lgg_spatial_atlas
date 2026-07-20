"""Atlas config: cells (genes/cell type/niche, paper colours) + native MS ion-density
layer (m/z intensity over aligned MS spots), side by side in the same frame."""
import sys, json
from vitessce import VitessceConfig, ViewType as vt, AnnDataWrapper, CoordinationType as ct

CELL_Z, MS_Z, OUT, PAL = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
pal = json.load(open(PAL))
def rgb(hx, fb="#888888"):
    hx=(hx or fb).lstrip("#"); hx = hx if len(hx)==6 else fb.lstrip("#")
    return [int(hx[i:i+2],16) for i in (0,2,4)]

vc = VitessceConfig(schema_version="1.0.16", name="LGG pt2 - ven2_z1",
    description="Venture pt2 (ven2) z1: genes + cell types + niches (cells) and m/z ion density (MS spots)")

# --- dataset 1: Xenium cells ---
w_cells = AnnDataWrapper(
    adata_url=CELL_Z,
    obs_embedding_paths=["obsm/spatial","obsm/X_umap"],
    obs_embedding_names=["Spatial","UMAP"],
    obs_set_paths=["obs/cell_type","obs/niche"],
    obs_set_names=["Cell Type","Niche"],
    obs_feature_matrix_path="X",
    feature_filter_path="var/is_gene",          # genes only; metabolites come from the MS layer
)
ds_cells = vc.add_dataset(name="Cells (ven2_z1)").add_object(w_cells)

# --- dataset 2: native MS ion-density spots ---
w_ms = AnnDataWrapper(
    adata_url=MS_Z,
    obs_embedding_paths=["obsm/spatial"],
    obs_embedding_names=["Spatial"],
    obs_feature_matrix_path="X",
)
ds_ms = vc.add_dataset(name="Metabolites (MS spots)").add_object(w_ms)

sp_cells = vc.add_view(vt.SCATTERPLOT, dataset=ds_cells, mapping="Spatial")
sp_ms    = vc.add_view(vt.SCATTERPLOT, dataset=ds_ms,    mapping="Spatial")
osets    = vc.add_view(vt.OBS_SETS,     dataset=ds_cells)
fl_gene  = vc.add_view(vt.FEATURE_LIST, dataset=ds_cells)
fl_met   = vc.add_view(vt.FEATURE_LIST, dataset=ds_ms)

# paper palette for cell types + niches
color_val = ([{"path":["Cell Type",c],"color":rgb(h)} for c,h in pal["cell_type"].items()]
           + [{"path":["Niche",c],"color":rgb(h)} for c,h in pal["niche"].items()])
vc.link_views([sp_cells, osets], [ct.OBS_SET_COLOR], [color_val])
# continuous colormap for ion density (matches the notebook's viridis)
vc.link_views([sp_ms, fl_met], [ct.FEATURE_VALUE_COLORMAP], ["viridis"])

vc.layout((sp_cells | sp_ms) / (osets | (fl_gene | fl_met)))
cfg = vc.to_dict()
VitessceConfig.from_dict(cfg)          # validate round-trip
json.dump(cfg, open(OUT,"w"), indent=2)
print("VALID | datasets:", len(cfg["datasets"]),
      "| views:", [v["component"] for v in cfg["layout"]])
