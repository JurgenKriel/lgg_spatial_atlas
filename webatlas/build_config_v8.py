"""Atlas config: cells (genes/cell type/niche) + MS ion-density layer, with
INDEPENDENT feature selection per layer so a metabolite click never touches the
transcriptomics panel (and vice versa)."""
import sys, json
from vitessce import VitessceConfig, ViewType as vt, AnnDataWrapper, CoordinationType as ct

CELL_Z, MS_Z, OUT, PAL = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
pal = json.load(open(PAL))
def rgb(hx, fb="#888888"):
    hx=(hx or fb).lstrip("#"); hx = hx if len(hx)==6 else fb.lstrip("#")
    return [int(hx[i:i+2],16) for i in (0,2,4)]

vc = VitessceConfig(schema_version="1.0.16", name="LGG pt2 - ven2_z1",
    description="Venture pt2 (ven2) z1: genes + cell types + niches (cells); m/z ion density (MS spots)")

# dataset A: Xenium cells -- featureType 'gene'
w_cells = AnnDataWrapper(
    adata_url=CELL_Z,
    obs_embedding_paths=["obsm/spatial","obsm/X_umap"],
    obs_embedding_names=["Spatial","UMAP"],
    obs_set_paths=["obs/cell_type","obs/niche"],
    obs_set_names=["Cell Type","Niche"],
    obs_feature_matrix_path="X",
    feature_filter_path="var/is_gene",
    coordination_values={"obsType":"cell","featureType":"gene"},
)
ds_cells = vc.add_dataset(name="Cells (ven2_z1)").add_object(w_cells)

# dataset B: MS spots -- featureType 'metabolite' (distinct => independent selection)
w_ms = AnnDataWrapper(
    adata_url=MS_Z,
    obs_embedding_paths=["obsm/spatial"],
    obs_embedding_names=["Spatial"],
    obs_feature_matrix_path="X",
    coordination_values={"obsType":"spot","featureType":"metabolite"},
)
ds_ms = vc.add_dataset(name="Metabolites (MS spots)").add_object(w_ms)

sp_cells = vc.add_view(vt.SCATTERPLOT, dataset=ds_cells, mapping="Spatial")
sp_ms    = vc.add_view(vt.SCATTERPLOT, dataset=ds_ms,    mapping="Spatial")
osets    = vc.add_view(vt.OBS_SETS,     dataset=ds_cells)
fl_gene  = vc.add_view(vt.FEATURE_LIST, dataset=ds_cells)
fl_met   = vc.add_view(vt.FEATURE_LIST, dataset=ds_ms)

# CRITICAL: declare featureType on the VIEWS too (file-only broke the loader before),
# and give each layer its own featureSelection + obsColorEncoding scope.
vc.link_views([sp_cells, fl_gene, osets], [ct.OBS_TYPE], ["cell"])
vc.link_views([sp_ms,    fl_met ], [ct.OBS_TYPE], ["spot"])
vc.link_views([sp_cells, fl_gene], [ct.FEATURE_TYPE], ["gene"])
vc.link_views([sp_ms,    fl_met ], [ct.FEATURE_TYPE], ["metabolite"])
vc.link_views([sp_cells, fl_gene], [ct.FEATURE_SELECTION], [None])
vc.link_views([sp_ms,    fl_met ], [ct.FEATURE_SELECTION], [None])
vc.link_views([sp_cells, fl_gene], [ct.OBS_COLOR_ENCODING], ["cellSetSelection"])
vc.link_views([sp_ms,    fl_met ], [ct.OBS_COLOR_ENCODING], ["geneSelection"])

color_val = ([{"path":["Cell Type",c],"color":rgb(h)} for c,h in pal["cell_type"].items()]
           + [{"path":["Niche",c],"color":rgb(h)} for c,h in pal["niche"].items()])
vc.link_views([sp_cells, osets], [ct.OBS_SET_COLOR], [color_val])
vc.link_views([sp_ms, fl_met], [ct.FEATURE_VALUE_COLORMAP], ["viridis"])

vc.layout((sp_cells | sp_ms) / (osets | (fl_gene | fl_met)))
cfg = vc.to_dict(); VitessceConfig.from_dict(cfg)
json.dump(cfg, open(OUT,"w"), indent=2)
print("VALID | datasets:", len(cfg["datasets"]))
for v in cfg["layout"]:
    print("  ", v["component"], v.get("coordinationScopes"))
