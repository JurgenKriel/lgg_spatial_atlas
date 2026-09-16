"""Atlas config for one (sample, z-plane).

Cells (genes / cell type / niche), optionally alongside an MS ion-density layer,
with INDEPENDENT feature selection per layer so a metabolite click never touches
the transcriptomics panel (and vice versa).

Two things this handles that the pt2-only version did not:

  * MS is OPTIONAL. Most of the cohort is ST-only, and those samples must get a
    single full-width cells panel — not a dead empty MS panel. Pass "" or "none"
    as the MS store.
  * The config's name/description/dataset titles are DERIVED from the sample and
    plane, not literals. The previous version hard-coded "ven2_z1" into every
    config it produced, so every plane's config claimed to be z1.

Usage:
    build_config_v8.py CELLS_ZARR MS_ZARR OUT PAL [BASE_URL] [--sample S] [--z N]

    MS_ZARR may be "" , "-" or "none" for an ST-only sample.
    BASE_URL, if given, is prefixed to store names that are not already absolute
    (component D-5), so one build targets any host without a rebuild.
    --sample / --z override what is inferred from the cells store filename.
"""
import argparse
import json
import os
import re
import sys

from vitessce import VitessceConfig, ViewType as vt, AnnDataWrapper, CoordinationType as ct

NO_MS = {"", "-", "none", "None", "null", "NA"}


def parse_args(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("cells")
    ap.add_argument("ms", help='MS store, or "" / "none" for an ST-only sample')
    ap.add_argument("out")
    ap.add_argument("pal")
    ap.add_argument("base", nargs="?", default="")
    ap.add_argument("--sample", default=None)
    ap.add_argument("--z", default=None)
    ap.add_argument("--release-dir", default=None,
                    help="where the stores live, for checking which embeddings "
                         "exist (default: the directory of OUT)")
    return ap.parse_args(argv)


def infer_sample_z(store):
    """Pull sample and z from '<prefix>-<sample>_z<N>-anndata.zarr'.

    Same convention deploy/make_manifest.py keys off, so a config and the
    manifest can never disagree about which plane a file is.
    """
    m = re.search(r"-([A-Za-z0-9._-]+)_z(\d+)-anndata\.zarr$", store.rstrip("/"))
    if m:
        return m.group(1), int(m.group(2))
    return None, None


def available_embeddings(store, release_dir):
    """Which obsm/* embeddings the store ACTUALLY contains.

    Declaring an embedding that is not there makes Vitessce fail to load the
    dataset and render nothing — a blank panel with no obvious cause. The pilot
    declared obsm/X_umap and got away with it only because the Nextflow step
    (compute_embeddings: True) created it; a build that writes zarr directly
    never does. So read the store rather than assume.

    Returns None when the store cannot be inspected, and the caller then falls
    back to spatial alone, which every store has.
    """
    name = store.rstrip("/").split("/")[-1]
    path = os.path.join(release_dir or ".", name, ".zmetadata")
    try:
        with open(path) as fh:
            meta = json.load(fh)["metadata"]
    except (OSError, KeyError, ValueError):
        return None
    found = set()
    for key in meta:
        m = re.match(r"^obsm/([^/]+)/\.zarray$", key)
        if m:
            found.add(m.group(1))
    return found


def embedding_args(store, release_dir, candidates):
    avail = available_embeddings(store, release_dir)
    if avail is None:
        pairs = [(p, n) for p, n in candidates if p.endswith("spatial")]
    else:
        pairs = [(p, n) for p, n in candidates if p.split("/")[-1] in avail]
    if not pairs:
        raise SystemExit(f"{store}: no usable embedding found (need at least obsm/spatial)")
    return [p for p, _ in pairs], [n for _, n in pairs]


def rgb(hx, fb="#888888"):
    hx = (hx or fb).lstrip("#")
    hx = hx if len(hx) == 6 else fb.lstrip("#")
    return [int(hx[i:i + 2], 16) for i in (0, 2, 4)]


def main(argv):
    a = parse_args(argv)

    def resolve(u):
        if not a.base or not u or u.startswith(("http://", "https://", "/")):
            return u
        return a.base.rstrip("/") + "/" + u.lstrip("/")

    cells_url = resolve(a.cells)
    ms_raw = (a.ms or "").strip()
    has_ms = ms_raw not in NO_MS
    ms_url = resolve(ms_raw) if has_ms else None

    sample, z = infer_sample_z(a.cells)
    if a.sample:
        sample = a.sample
    if a.z is not None:
        z = int(a.z)
    # Don't append "z2" when the sample id already ends in _z2.
    base = f"{sample or 'sample'}"
    label = base if (z is None or base.endswith(f"_z{z}")) else f"{base} z{z}"

    release_dir = a.release_dir or os.path.dirname(os.path.abspath(a.out))
    cell_paths, cell_names = embedding_args(
        a.cells, release_dir,
        [("obsm/spatial", "Spatial"), ("obsm/X_umap", "UMAP")])
    print(f"   embeddings : {', '.join(cell_names)}")

    pal = json.load(open(a.pal))

    layers = "genes + cell types + niches (cells)"
    if has_ms:
        layers += "; m/z ion density (MS spots)"
    vc = VitessceConfig(
        schema_version="1.0.16",
        name=f"Venture Atlas - {label}",
        description=f"Venture {label}: {layers}",
    )

    # --- dataset A: Xenium cells, featureType 'gene' -------------------------
    w_cells = AnnDataWrapper(
        adata_url=cells_url,
        obs_embedding_paths=cell_paths,
        obs_embedding_names=cell_names,
        obs_set_paths=["obs/cell_type", "obs/niche"],
        obs_set_names=["Cell Type", "Niche"],
        obs_feature_matrix_path="X",
        feature_filter_path="var/is_gene",
        coordination_values={"obsType": "cell", "featureType": "gene"},
    )
    ds_cells = vc.add_dataset(name=f"Cells ({label})").add_object(w_cells)

    sp_cells = vc.add_view(vt.SCATTERPLOT, dataset=ds_cells, mapping="Spatial")
    osets = vc.add_view(vt.OBS_SETS, dataset=ds_cells)
    fl_gene = vc.add_view(vt.FEATURE_LIST, dataset=ds_cells)

    # CRITICAL: declare obsType/featureType on the VIEWS too — file-only broke
    # the loader before — and give each layer its own featureSelection and
    # obsColorEncoding scope.
    vc.link_views([sp_cells, fl_gene, osets], [ct.OBS_TYPE], ["cell"])
    vc.link_views([sp_cells, fl_gene], [ct.FEATURE_TYPE], ["gene"])
    vc.link_views([sp_cells, fl_gene], [ct.FEATURE_SELECTION], [None])
    vc.link_views([sp_cells, fl_gene], [ct.OBS_COLOR_ENCODING], ["cellSetSelection"])

    color_val = (
        [{"path": ["Cell Type", c], "color": rgb(h)} for c, h in pal["cell_type"].items()]
        + [{"path": ["Niche", c], "color": rgb(h)} for c, h in pal["niche"].items()]
    )
    vc.link_views([sp_cells, osets], [ct.OBS_SET_COLOR], [color_val])

    if has_ms:
        # --- dataset B: MS spots, featureType 'metabolite' -------------------
        # A distinct obsType is what stops selecting a metabolite from also
        # driving the transcriptomics panel.
        w_ms = AnnDataWrapper(
            adata_url=ms_url,
            obs_embedding_paths=["obsm/spatial"],
            obs_embedding_names=["Spatial"],
            obs_feature_matrix_path="X",
            coordination_values={"obsType": "spot", "featureType": "metabolite"},
        )
        ds_ms = vc.add_dataset(name=f"Metabolites ({label})").add_object(w_ms)
        sp_ms = vc.add_view(vt.SCATTERPLOT, dataset=ds_ms, mapping="Spatial")
        fl_met = vc.add_view(vt.FEATURE_LIST, dataset=ds_ms)

        vc.link_views([sp_ms, fl_met], [ct.OBS_TYPE], ["spot"])
        vc.link_views([sp_ms, fl_met], [ct.FEATURE_TYPE], ["metabolite"])
        vc.link_views([sp_ms, fl_met], [ct.FEATURE_SELECTION], [None])
        vc.link_views([sp_ms, fl_met], [ct.OBS_COLOR_ENCODING], ["geneSelection"])
        vc.link_views([sp_ms, fl_met], [ct.FEATURE_VALUE_COLORMAP], ["viridis"])

        vc.layout((sp_cells | sp_ms) / (osets | (fl_gene | fl_met)))
    else:
        # ST-only: the cells panel takes the full width. No empty second panel.
        vc.layout(sp_cells / (osets | fl_gene))

    cfg = vc.to_dict()
    VitessceConfig.from_dict(cfg)   # round-trip validation before writing
    json.dump(cfg, open(a.out, "w"), indent=2)

    print(f"VALID | {label} | datasets: {len(cfg['datasets'])} | MS: {'yes' if has_ms else 'no'}")
    for v in cfg["layout"]:
        print("  ", v["component"], v.get("coordinationScopes"))


if __name__ == "__main__":
    main(sys.argv[1:])
