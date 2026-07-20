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

## Non-Functional / Quality

- **REQ-Q1** — All heavy steps run under SLURM; large arrays handled via
  Dask/zarr streaming, never full in-memory loads of whole-slide data.
- **REQ-Q2** — Pipeline output zarr is v2-compatible (down-convert if v3).
- **REQ-Q3** — The AnnData build is a scripted, re-runnable step (no manual
  notebook-only surgery) with logged provenance (source file hashes, cell
  counts, matched fraction).
- **REQ-Q4** — The semantic-analysis root `.planning/` and `results/` are left
  byte-unchanged by this work.
