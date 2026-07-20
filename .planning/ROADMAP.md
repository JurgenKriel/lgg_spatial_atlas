# Roadmap: Venture Multi-Omic Web Atlas

## Overview

Build a Vitessce web atlas of the Venture cohort via the haniffalab
webatlas-pipeline, augmented with a custom pre-step that fuses ST genes,
aligned MS metabolites, cell types, and niches into per-sample AnnData. Deliver
a working **4-modality viewer for pt2** first, then generalize the builder to
the full cohort.

**Execution order:** 1 → 2 → 3 → 4 → 5 → 6
**Pilot boundary:** Phases 1–5 deliver the pt2 pilot. Phase 6 scales out.

## Phases

- [x] **Phase 1: Pipeline bootstrap** — Get webatlas-pipeline (Nextflow) running on HPC against example data; pin versions/containers. [REQ-01]
- [ ] **Phase 2: pt2 AnnData assembly (the fusion core)** — Extract + join genes, metabolites, cell type, niche, centroids into per-sample `h5ad`; validate the three-way cell join. [REQ-02, REQ-03]
- [ ] **Phase 3: webatlas config + Vitessce build (pt2)** — Author params YAML, run pipeline, produce a Vitessce config exposing Gene/Metabolite/Cell type/Niche selectors. [REQ-04, REQ-05]
- [ ] **Phase 4: Viewer UX — samples, z-planes, feature-type grouping** — Sample switcher, per-z-plane view, palette wiring, distinct Gene vs Metabolite dropdowns. [REQ-06]
- [ ] **Phase 5: Deployment & sharing** — Serve or statically export the pt2 atlas with documented collaborator access. [REQ-07]
- [ ] **Phase 6: Generalize to full cohort + pt5 metabolites** — Batch the builder across ~29 samples; enable metabolite layer for pt5; graceful absence elsewhere. [REQ-08]

## Phase Details

### Phase 1: Pipeline bootstrap
**Goal**: Have a reproducible webatlas-pipeline install running on HPC (Nextflow + Singularity) that produces a Vitessce config from the pipeline's own example data, so the downstream contract (what the pipeline expects and emits) is known before we build custom inputs.
**Depends on**: Nothing
**Requirements**: REQ-01, REQ-Q1
**Success Criteria** (what must be TRUE):
  1. `nextflow run main.nf -params-file <example> -entry Full_pipeline` completes on HPC without error under SLURM.
  2. The pipeline version, Nextflow version, and container digests are pinned in a config file committed to `venture_atlas/`.
  3. A written note documents the exact AnnData/`obs`/`var`/`obsm` conventions and the params-YAML schema the pipeline consumes (spatial coords, obsSets, feature/embedding options).
  4. The example Vitessce output opens in a browser locally (port-forward or static serve).
**Plans**: 1 plan (01-01)

### Phase 2: pt2 AnnData assembly (the fusion core)
**Goal**: Produce, from real pt2 data, one AnnData `h5ad` per pt2 sample that carries gene expression, aligned metabolite features, cell-type, niche, and centroid coordinates — with the three-way cell join validated and a matched-cell fraction reported. This is the highest-risk, highest-value phase.
**Depends on**: Phase 1 (AnnData conventions known)
**Requirements**: REQ-02, REQ-03, REQ-Q2, REQ-Q3
**Success Criteria** (what must be TRUE):
  1. A scripted builder reads: pt2 cells from `ven_all_250217.rds` (genes), pt2 `*_centroids.zarr` (`Anno`, `niche`, centroids), and `integrated_data_250925.rds` (metabolites), and writes per-sample `h5ad`.
  2. The shared join key is identified and the matched-cell fraction (Seurat∩centroids∩metabolomics) is logged; the build asserts it exceeds a documented threshold.
  3. Each `h5ad` has `obs.cell_type`, `obs.niche`, `obsm['spatial']`, gene vars, and metabolite features flagged distinctly (`var['feature_type']` ∈ {gene, metabolite} or a separate matrix).
  4. Cell-type and niche colour palettes are carried into `uns`.
  5. Output zarr/h5ad is zarr-v2 compatible; provenance (source hashes, counts, matched fraction) is written alongside.
**Plans**: 2 plans (02-01 extract+key-resolution, 02-02 fuse+write+validate)

### Phase 3: webatlas config + Vitessce build (pt2)
**Goal**: Turn the pt2 `h5ad`(s) into a Vitessce atlas via the pipeline, with a config that surfaces all four layers as user-selectable.
**Depends on**: Phase 2
**Requirements**: REQ-04, REQ-05
**Success Criteria** (what must be TRUE):
  1. A params YAML references the pt2 `h5ad`(s) and runs through webatlas-pipeline to a Vitessce config + data zarr.
  2. In the viewer, all four selectors work on pt2: colour cells by a chosen Gene, a chosen Metabolite, Cell type, and Niche.
  3. Metabolites are selectable as a feature set distinct from genes (validated in the running viewer, not just in the file).
  4. Cell-type/niche categories render with the zarr `uns` palettes.
**Plans**: TBD at plan-time (est. 2)

### Phase 4: Viewer UX — samples, z-planes, feature-type grouping
**Goal**: Make the atlas usable across pt2's samples and 8 z-planes with clean feature grouping.
**Depends on**: Phase 3
**Requirements**: REQ-06
**Success Criteria** (what must be TRUE):
  1. A sample switcher lists pt2 samples; selecting one loads its data.
  2. Per-z-plane data (z1..z8) is selectable or visually separable.
  3. Gene and Metabolite are presented as separate labelled dropdowns (not one merged feature list).
**Plans**: TBD at plan-time (est. 1–2)

### Phase 5: Deployment & sharing
**Goal**: Collaborators can open the pt2 atlas with documented steps.
**Depends on**: Phase 4
**Requirements**: REQ-07
**Success Criteria** (what must be TRUE):
  1. The atlas is served (or statically exported) and reachable by a second user following written instructions.
  2. Data-serving approach (static files vs http server, HPC port-forward vs export) is decided and documented.
**Plans**: TBD at plan-time (est. 1)

### Phase 6: Generalize to full cohort + pt5 metabolites
**Goal**: Run the builder across all ~29 samples; enable metabolites for pt5; degrade gracefully where metabolomics is absent.
**Depends on**: Phase 5 (pilot proven end-to-end)
**Requirements**: REQ-08, REQ-Q4
**Success Criteria** (what must be TRUE):
  1. The AnnData builder is parameterized by sample and run (batched under SLURM) across the cohort.
  2. pt5 gets a Metabolite layer from `integrated_data_250926_2.rds`; samples without metabolomics build cleanly with the Metabolite selector absent.
  3. The multi-sample atlas config lists all built samples in the switcher.
  4. Root `.planning/` and semantic `results/` are byte-unchanged.
**Plans**: TBD at plan-time (est. 2–3)

## Progress

| Phase | Plans | Status |
|-------|-------|--------|
| 1. Pipeline bootstrap | 1/1 | **Complete** (2026-07-20) |
| 2. pt2 AnnData assembly | 0/2 | Planned |
| 3. webatlas config + build | 0/? | Roadmapped |
| 4. Viewer UX | 0/? | Roadmapped |
| 5. Deployment | 0/? | Roadmapped |
| 6. Cohort generalization | 0/? | Roadmapped |

## Key Risks & Open Questions (resolve during phase execution)

1. **Cell join key** — Does the SpaMTP integrated object share ST cell barcodes
   / `cell_id` with the centroids zarr and the Seurat cohort object? Phase 2
   must resolve this first; if keys differ, fall back to spatial nearest-neighbour
   on centroids (with a distance threshold).
2. **Metabolite as a Vitessce feature type** — Confirm webatlas-pipeline can
   expose a second feature matrix / feature-type so Metabolite is a distinct
   selector. If not, plan a light post-processing of the Vitessce config or a
   custom AnnData layout the pipeline accepts.
3. **Seurat → AnnData path** — `zellkonverter`/`sceasy` vs writing counts+meta to
   intermediate files then assembling in Python. Decide in Phase 2 based on
   object size (1.2 GB / 2.0 GB) and memory.
4. **Coordinate frames** — Genes (Seurat), centroids (zarr), and metabolites
   (integrated) must share one coordinate space per sample/z-plane; verify the
   "aligned" metabolomics is in the ST centroid frame.
