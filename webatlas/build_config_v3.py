"""Build a VALID Vitessce config via the vitessce API: spatial+umap scatter, obs sets
(paper colors via obsSetColor), and separate Gene + Metabolite feature lists."""
import sys, json
from vitessce import VitessceConfig, ViewType as vt, AnnDataWrapper, CoordinationType as ct

Z   = sys.argv[1]
OUT = sys.argv[2]
pal = json.load(open(sys.argv[3]))

def rgb(hx, fb="#888888"):
    hx=(hx or fb).lstrip("#"); hx = hx if len(hx)==6 else fb.lstrip("#")
    return [int(hx[i:i+2],16) for i in (0,2,4)]

vc = VitessceConfig(schema_version="1.0.16", name="LGG pt2 - ven2_z1",
                    description="Venture pt2 (ven2) z1 - genes, metabolites, cell types, niches")

# base wrapper: embeddings + sets (no matrix)
w_obs = AnnDataWrapper(
    adata_url=Z,
    obs_embedding_paths=["obsm/spatial","obsm/X_umap"],
    obs_embedding_names=["Spatial","UMAP"],
    obs_set_paths=["obs/cell_type","obs/niche"],
    obs_set_names=["Cell Type","Niche"],
    coordination_values={"obsType":"cell"},
)
# gene + metabolite feature matrices (filtered by var flag), distinct featureType
w_gene = AnnDataWrapper(adata_url=Z, obs_feature_matrix_path="X",
    feature_filter_path="var/is_gene",
    coordination_values={"obsType":"cell","featureType":"gene"})
w_metab = AnnDataWrapper(adata_url=Z, obs_feature_matrix_path="X",
    feature_filter_path="var/is_metabolite",
    coordination_values={"obsType":"cell","featureType":"metabolite"})

ds = vc.add_dataset(name="ven2_z1").add_object(w_obs).add_object(w_gene).add_object(w_metab)

sp  = vc.add_view(vt.SCATTERPLOT, dataset=ds, mapping="Spatial")
um  = vc.add_view(vt.SCATTERPLOT, dataset=ds, mapping="UMAP")
oss = vc.add_view(vt.OBS_SETS, dataset=ds)
fg  = vc.add_view(vt.FEATURE_LIST, dataset=ds)   # genes
fm  = vc.add_view(vt.FEATURE_LIST, dataset=ds)   # metabolites

# paper colors -> obsSetColor, linked to the colour-bearing views
color_val = ([{"path":["Cell Type",c],"color":rgb(h)} for c,h in pal["cell_type"].items()]
           + [{"path":["Niche",c],"color":rgb(h)} for c,h in pal["niche"].items()])
vc.link_views([sp,um,oss], [ct.OBS_SET_COLOR], [color_val])
# feature lists to their feature types
vc.link_views([fg], [ct.FEATURE_TYPE], ["gene"])
vc.link_views([fm], [ct.FEATURE_TYPE], ["metabolite"])

vc.layout((sp | um) / (oss | (fg | fm)))
cfg = vc.to_dict()

# validate round-trip
VitessceConfig.from_dict(cfg)
json.dump(cfg, open(OUT,"w"), indent=2)
fls=[v for v in cfg["layout"] if v["component"]=="featureList"]
print("VALID | featureLists:", len(fls), "| obsSetColor in space:", "obsSetColor" in cfg["coordinationSpace"])
