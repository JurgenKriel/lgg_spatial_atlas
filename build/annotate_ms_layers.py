"""Add metabolite annotations to already-built MS ion-density zarrs, in place.

Only the `var` group is rewritten (X/obs/obsm untouched); the feature index becomes
the readable label (e.g. 'D-Glucose [M+Na] · m/z 203.0533', unannotated peaks
'm/z 72.0799') so Vitessce's feature list shows names. Old ids go to var/mz_id.

Usage: python annotate_ms_layers.py <ms-anndata.zarr> <sample> <z> [...more triples]
  e.g. python annotate_ms_layers.py ../docs/atlas/ms_ven2_z1-anndata.zarr ven2 z1
"""
import sys
import anndata as ad, zarr
from anndata.experimental import read_elem, write_elem
from metabolite_annotations import annotate_var

args = sys.argv[1:]
assert args and len(args) % 3 == 0, __doc__
for path, sample, z in zip(args[0::3], args[1::3], args[2::3]):
    g = zarr.open_group(path, mode="r+")
    var = read_elem(g["var"])
    if "mz_id" in var:                      # re-run: restore the original index first
        var = var.set_index("mz_id")
        var.index.name = None
        var = var[[c for c in ("raw_mz", "feature_type", "is_metabolite") if c in var]]
    var = annotate_var(var, sample, z)
    assert len(var) == g["X"].shape[1]
    del g["var"]
    write_elem(g, "var", var)
    zarr.consolidate_metadata(path)
    ad.read_zarr(path)                      # round-trip check
    print(f"{path}: {int(var.is_annotated.sum())}/{len(var)} m/z annotated "
          f"({(var.annotation_source.str.startswith('targeted')).sum()} targeted-panel)")
