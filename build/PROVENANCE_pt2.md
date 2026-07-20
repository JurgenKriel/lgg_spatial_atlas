# pt2 AnnData Build — Provenance (Phase 2 / 02-02) 2026-07-20

## Sources
- `/vast/projects/BCRL_Multi_Omics/venture_pt2/integrated/integrated_data_250925.rds`  (2.0G, mtime 2025-09-29)
- `/vast/projects/BCRL_Multi_Omics/venture_ST/full_ven_cohort_annotations.csv`  (790M, mtime 2026-04-09)
- `/vast/scratch/users/kriel.j/centroids_2/ven2_centroids.zarr`  (23M, mtime 2026-07-11)

## Build
- Genes: SPT assay (339, 'data' layer). Metabolites: SPM assay (857, 'data' layer).
- niche joined from cohort CSV (patient=ven2) on (z-plane, cell_id); 100% matched all planes.
- One h5ad per z-plane: X = [genes | metabolites] (var.feature_type); obs.cell_type=Anno, obs.niche;
  obsm.spatial = x/y_centroid (+ spatial_aligned); uns palettes from ven2 centroids zarr.
- Envs: R 4.5.3 (SeuratObject/Matrix, JoinLayers); Python spatialdata_env_2 (anndata 0.11.3).
- Scripts: build/export_pt2_matrices.R -> build/build_pt2_anndata.py -> build/validate_pt2_anndata.py

## Per-z-plane summary
```
sample,z,cells,genes,metabolites,niche_matched,niche_frac,file
6901_2,ven2_z1,40107,339,857,40107,1.0,/vast/scratch/users/kriel.j/atlas_pt2/h5ad/pt2_ven2_z1.h5ad
6901_1,ven2_z2,31386,339,857,31386,1.0,/vast/scratch/users/kriel.j/atlas_pt2/h5ad/pt2_ven2_z2.h5ad
6889_2,ven2_z3,47450,339,857,47450,1.0,/vast/scratch/users/kriel.j/atlas_pt2/h5ad/pt2_ven2_z3.h5ad
6889_1,ven2_z4,42513,339,857,42513,1.0,/vast/scratch/users/kriel.j/atlas_pt2/h5ad/pt2_ven2_z4.h5ad
6694_2,ven2_z5,39834,339,857,39834,1.0,/vast/scratch/users/kriel.j/atlas_pt2/h5ad/pt2_ven2_z5.h5ad
6694_1,ven2_z6,42565,339,857,42565,1.0,/vast/scratch/users/kriel.j/atlas_pt2/h5ad/pt2_ven2_z6.h5ad
6687_2,ven2_z7,42032,339,857,42032,1.0,/vast/scratch/users/kriel.j/atlas_pt2/h5ad/pt2_ven2_z7.h5ad
6687_1,ven2_z8,48508,339,857,48508,1.0,/vast/scratch/users/kriel.j/atlas_pt2/h5ad/pt2_ven2_z8.h5ad
```

## Output
h5ad in /vast/scratch/users/kriel.j/atlas_pt2/h5ad/ (gitignored; large). 8 files, 1196 features each.
