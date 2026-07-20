# HANDOFF — resume state (2026-07-20)

Repo: **github.com/JurgenKriel/lgg_spatial_atlas** (working tree
`/vast/projects/BCRL_Multi_Omics/venture_atlas`, nested inside the BCRL checkout).
Live viewer: **https://jurgenkriel.github.io/lgg_spatial_atlas/**

## Status
Phases 1–3 complete; Phase 4 substantially done (z-slider, 3 planes, paper colours,
independent gene/metabolite selection). Milestone 2 (production viewer) is planned,
not started. User verdict: "demo is good enough as a concept".

## What's live
- pt2 (ven2), planes **z1–z3**. Per plane, two side-by-side scatterplots:
  - **cells** — 339 Xenium genes, `cell_type` (23), `niche` (10), paper palette
  - **MS ion density** — native MS spot grid coloured by chosen m/z (viridis)
- Z-slider in `docs/index.html` (iframes vitessce.io, dynamic cache-buster).
- 708MB on Pages (z1 cell 127M, z2 88M, z3 230M; MS 49/88/129M).

## Data pipeline (all scripts in repo)
1. `build/export_pt2_matrices.R` — from `venture_pt2/integrated/integrated_data_250925.rds`
   (Seurat: `SPT`=339 genes, `SPM`=857 m/z, 334,395 cells, `Anno`, centroids).
   Needs `JoinLayers` (v5 split layers); do **not** `subset()` (SlideSeq image validation bug).
2. `build/build_pt2_anndata.py` — fuses genes+metabolites, joins `niche` from
   `venture_ST/full_ven_cohort_annotations.csv` on (z-plane, cell_id) — **100% matched**.
3. `build/build_ms_layers.py` — native MS ion-density layers from
   `venture_pt2/aligned_metabolites/*.txt` (tab-sep; `x,y` + `X<mz>` + transformed).
   **Use `transformed_x/y`** (verified aligned; raw `x/y` is not).
4. `webatlas/build_config_v8.py` — the CURRENT config builder (vitessce API).

## Hard-won gotchas (do not regress)
- **Build configs with the vitessce python API and validate `VitessceConfig.from_dict`.**
  A hand-written config silently failed on a missing `description`.
- **X must be DENSE** (`encoding-type: array`). Sparse CSR → `LoaderNotFoundError`.
- **Declare `obsType`/`featureType` on BOTH the file `coordinationValues` AND the views.**
  File-only → LoaderNotFound; neither → the two layers couple.
- **Layers must differ in `obsType`** (`cell` vs `spot`) or selecting a metabolite
  also drives the transcriptomics panel.
- Points-only data: the classic `spatial` view renders nothing — use a **SCATTERPLOT**
  on `obsm/spatial`.
- Paper colours require explicit **`obsSetColor`**; palettes are in `webatlas/pt2/palettes.json`
  (sourced from `centroids_2/ven2_centroids.zarr` `Anno_color`/`niche_color`).
- Numba/scanpy fail in the read-only container → always pass `-c webatlas/smoke/extra.config`.
- GitHub Pages needs **`.nojekyll`** or zarr dotfiles (`.zgroup`/`.zarray`) 404.
- Cache-busters must be **dynamic**; a static one hid config updates for a whole round.

## Open risks
- **z-plane labels:** cell h5ads built as `z1`/`z2` are SWAPPED vs real section order.
  Configs cross-reference (viewer z1 = cells `z2` + MS `z1`). See
  `webatlas/pt2/ST_MS_PLANE_MAPPING.md`. **z3–z8 pairings UNVERIFIED** — footprint
  overlap can't resolve them (all pairs .70–.83, same tissue block).
- **Hosting ceiling:** cohort will not fit on Pages (see Phase 10).
- z2's MS grid covers more area than its cells (within-50u 0.58 vs 0.99 for z1) —
  likely MS capture over background, worth a visual check.

## Cohort coverage (verified)
15 ST samples; **6 with matched SM** = ven1–ven6
(`venture_pt{1..6}/metabolomics_edge_removed/*_with_xy.csv`; pt2 also `aligned_metabolites/`).
ST-only: GL0018, GL0043, GL0048, GL0097, GL0184, GX008, LGG-A/B/C.
An earlier note claiming SM was pt2/pt5-only was WRONG (based only on `integrated/*.rds`).

## Next
Phase 6 (sample selector + manifest) and Milestone 2 Phase 10 (object storage) —
hosting gates the rest. Phase 8 (image + segmentation layers) is the biggest visual win.
