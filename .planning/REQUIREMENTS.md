# REQUIREMENTS: Venture Multi-Omic Web Atlas

Requirement IDs are referenced by ROADMAP phases and PLAN frontmatter.

## Functional

- **REQ-01** — The webatlas-pipeline (Nextflow) runs reproducibly on HPC and
  produces a Vitessce-loadable output on bundled/example input.
- **REQ-02** — For pt2, a per-sample AnnData `h5ad` is produced containing:
  gene expression (`.X`/`var`), `obs.cell_type` (from `Anno`), `obs.niche`,
  `obsm['spatial']` centroids, and aligned metabolite features distinguishable
  from genes (feature-type flag or separate matrix).
- **REQ-03** — The three-way cell join (Seurat ↔ centroids zarr ↔ integrated
  metabolomics) is performed on a shared key and the matched-cell fraction is
  reported and asserted above a threshold.
- **REQ-04** — The Vitessce viewer for pt2 exposes four independent selectors —
  **Gene, Metabolite, Cell type, Niche** — each colouring the spatial view.
- **REQ-05** — Cell-type and niche colours use the palettes stored in the
  centroids zarr `uns` (`Anno_colors`, `niche_colors`).
- **REQ-06** — A sample switcher lets the user pick a sample; per-z-plane data
  (z1..z8) is selectable/visible.
- **REQ-07** — The atlas is deployable so collaborators can open it (served
  Vitessce or static export) with documented access steps.
- **REQ-08** — The AnnData builder generalizes across all ~29 cohort samples;
  Metabolite layer is enabled for pt2 and pt5, gracefully absent elsewhere.

- **REQ-09** — The viewer provides a **sample selector** spanning all cohort ST
  samples (15: ven1–ven6, GL0018, GL0043, GL0048, GL0097, GL0184, GX008, LGG-A/B/C),
  in addition to the per-sample z-plane slider.
- **REQ-10** — A single viewer accommodates **both** matched ST+SM samples and
  ST-only samples: the Metabolite (MS ion-density) panel is present for the 6
  matched samples (ven1–ven6) and cleanly absent — not broken/empty — for the 9
  ST-only samples. Layout must not leave a dead panel.
- **REQ-11** — Sample/plane availability is driven by a generated manifest
  (sample → z-planes → which modalities exist), so the selector is data-driven
  rather than hard-coded.

## Non-Functional / Quality

- **REQ-Q1** — All heavy steps run under SLURM; large arrays handled via
  Dask/zarr streaming, never full in-memory loads of whole-slide data.
- **REQ-Q2** — Pipeline output zarr is v2-compatible (down-convert if v3).
- **REQ-Q3** — The AnnData build is a scripted, re-runnable step (no manual
  notebook-only surgery) with logged provenance (source file hashes, cell
  counts, matched fraction).
- **REQ-Q4** — The semantic-analysis root `.planning/` and `results/` are left
  byte-unchanged by this work.

## Milestone 2 — Production viewer (target: gbmspace.org / cellatlas.io quality)

- **REQ-12** — Replace the raw `vitessce.io?url=` iframe with a **self-hosted
  webatlas-app** frontend (github.com/haniffalab/webatlas-app — what cellatlas.io
  runs), giving a proper study/dataset browser instead of a bare config URL.
- **REQ-13** — Add **raster image layers** (H&E and/or IF) per sample/plane as
  OME-Zarr, so molecular layers overlay real tissue rather than sitting on blank space.
- **REQ-14** — Add **cell segmentation polygons** (label images) so cells render as
  true boundaries; this also unlocks webatlas's native spatial view (it only lays out
  a spatial view when `is_spatial` AND an image exist).
- **REQ-15** — **Histopathology / region annotations** as a selectable layer,
  correlated with molecular layers (gbmspace shows annotations per tissue location).
- **REQ-16** — **Curated views**: named presets (e.g. "manuscript figure N") that open
  a specific sample/plane/feature/colour configuration.
- **REQ-17** — **Comparison mode**: view two samples or planes side by side with
  linked zoom/pan.
- **REQ-18** — A **landing/about site** (study description, cohort table, methods,
  citation) wrapping the viewer, as gbmspace.org does.
- **REQ-19** — **Object-storage hosting** (Cloudflare R2 / S3 + CORS) replacing
  GitHub Pages; Pages cannot hold the cohort (3 planes of ONE sample = 708MB).
