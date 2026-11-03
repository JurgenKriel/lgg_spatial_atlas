# LGG Multi-Omic Web Atlas

Interactive web atlas of the Venture brain-cancer cohort built with the
[haniffalab **webatlas-pipeline**](https://github.com/haniffalab/webatlas-pipeline)
(Nextflow → **Vitessce**). The viewer lets users browse each sample and toggle
four data layers: **Gene**, **Metabolite**, **Cell type**, and **Niche**.

## Status
Planning + Phase 1 (pipeline bootstrap) in progress. See `.planning/ROADMAP.md`.

## Layout
- `.planning/` — GSD project charter, requirements, roadmap, phase plans.
- `webatlas/` — pipeline bootstrap: pinned versions, container pull, run scripts,
  and `PIPELINE_CONTRACT.md` (the AnnData/params spec Phase 2/3 target).
- `build/` — (Phase 2) scripts that fuse ST genes + MS metabolites + cell type +
  niche + centroids into per-sample AnnData `h5ad`.

## Data sources (on WEHI HPC, not in this repo)
- Genes: `ST/.../ven_all_250217.rds` (Seurat cohort)
- Cell type / niche / centroids: `venture_ST/centroids/*_centroids.zarr` (SpatialData)
- Metabolomics (ven1–ven6): `venture_pt{N}/metabolomics_edge_removed/*_with_xy.csv`
  (pt2 also `aligned_metabolites/`)
- Metabolite annotations (ven2–ven6, per plane):
  `build/metabolite_annotations_ven2-6.tsv`, built by `build/metabolite_annotations.py` from
  `/stornext/Home/data/data/allstaff/k/kriel.j/Ven2_Ven3_Ven4_Ven5_Ven6_selected_peak_annotation.csv`;
  applied to MS zarrs by `build/annotate_ms_layers.py` (or at build time in `build_ms_layers.py`)

## Environment (WEHI HPC)
Nextflow + `apptainer/1.4.1`; see `webatlas/versions.env`. Container cache in
`/vast/scratch/users/kriel.j/singularity_cache`.
