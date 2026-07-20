# PROJECT: Venture Multi-Omic Web Atlas

**Created:** 2026-07-20
**Owner:** kriel.j
**Status:** Planning (pilot on pt2)

## Purpose

Build a web-based, interactive spatial atlas of the Venture brain-cancer cohort
using the [haniffalab **webatlas-pipeline**](https://github.com/haniffalab/webatlas-pipeline)
(Nextflow → **Vitessce**). The viewer must let a user browse each sample and
toggle between four data layers:

1. **Gene** expression (spatial transcriptomics)
2. **Metabolite** intensity (aligned MS metabolomics)
3. **Cell type** (`Anno`)
4. **Niche**

## Why this is its own initiative (not a phase of the semantic roadmap)

The root `.planning/` project ("Niche DEG Semantic Pathway Analysis") is a
different deliverable and is mid-execution (Phase 5). This atlas is unrelated
delivery work, so it lives in its own directory-scoped `.planning/`
(`venture_atlas/.planning/`), mirroring the existing
`scripts/lightsheet_pipeline/.planning/` precedent. The semantic roadmap is
left untouched.

## Data Inventory (verified 2026-07-20)

| Layer | Source | Format | Coverage | Notes |
|-------|--------|--------|----------|-------|
| Cell type + Niche + centroids | `venture_ST/centroids/*_centroids.zarr` | SpatialData 0.3.0 (zarr v2) | ~29 samples | `tables/cell_annotations` obs: `Anno`, `niche`, `region`, `sample_id`, `x/y/z_centroid`, `z_layer`, `cell_id`, `instance_id`; `points/centroids_<s>_z{1..8}`; palettes in `uns/Anno_colors`, `uns/niche_colors`. **No gene expression in these stores.** |
| Gene expression | `/stornext/.../ST/data/processed/ven_all_250217.rds` | Seurat RDS (1.2 GB) | Full cohort | Cohort ST object; genes + per-cell barcodes. |
| Metabolomics (aligned/integrated) | `venture_pt2/integrated/integrated_data_250925.rds` | Seurat/SpaMTP RDS (2.0 GB) | **pt2 only** | Aligned to ST. `venture_pt5/integrated/integrated_data_250926_2.rds` also exists (pt5). |
| Existing viewer (reference) | `Venture_Visualizer/app.R` | R Shiny (single file) | — | Prior art; different approach, not carried forward. |

## Hard Constraints (from data reality)

- **Metabolomics is available only for pt2 and pt5.** "Metabolite per sample"
  can only be honoured for those two. The Metabolite selector is
  present-where-available.
- **Cells are points (centroids), not segmentation masks.** No label-image
  tiffs exist. Cells are rendered as Vitessce spot/point data. Polygons are a
  later enhancement, not in the pilot.
- **Three-way cell join is the core technical risk:** Seurat cells ↔ centroids
  zarr cells ↔ integrated metabolomics cells must share a key (cell barcode /
  `cell_id`). This must be validated with a reported matched fraction before any
  viewer is built.
- **Zarr version discipline:** all local envs are zarr 2.x; SpatialData stores
  are v2. Any pipeline output written as zarr v3 must be down-converted
  (`scripts/convert_zarr_v3_to_v2.py`, copy `fill_value`).

## Pilot-first Strategy

Build the **full 4-modality viewer for pt2 alone** end-to-end (bootstrap →
AnnData → pipeline → viewer → hosting), then generalize the AnnData builder
across the cohort and enable pt5 metabolites (Phase 6).

## Environments

| Task | Env | Notes |
|------|-----|-------|
| Read SpatialData zarr, build AnnData | `spatialdata_env_2/` | anndata, spatialdata, zarr 2.x |
| Extract from Seurat / SpaMTP RDS | R 4.5.3 (`module load R/4.5.3`) + `SpaMTP_env` | `zellkonverter`/`sceasy` for Seurat→AnnData; `LD_LIBRARY_PATH=cellpose_env/lib` per project memory |
| webatlas-pipeline | Nextflow + Singularity/Docker | on HPC via SLURM |

## Non-Goals (this milestone)

- 3D volumetric rendering across z-planes (2D per-z-plane is enough for pilot).
- True cell-boundary polygons / label images.
- Metabolomics for samples other than pt2 (pt5 added in Phase 6).
- Public internet hosting with auth (internal/HPC access first).
