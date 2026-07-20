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
- [x] **Phase 2: pt2 AnnData assembly (the fusion core)** — Extract + join genes, metabolites, cell type, niche, centroids into per-sample `h5ad`; validate the three-way cell join. [REQ-02, REQ-03]
- [x] **Phase 3: webatlas config + Vitessce build (pt2)** — Author params YAML, run pipeline, produce a Vitessce config exposing Gene/Metabolite/Cell type/Niche selectors. [REQ-04, REQ-05]
- [ ] **Phase 4: Viewer UX — samples, z-planes, feature-type grouping** *(in progress: z-slider done for z1–z3; sample selector pending)* — Sample switcher, per-z-plane view, palette wiring, distinct Gene vs Metabolite dropdowns. [REQ-06]
- [ ] **Phase 5: Deployment & sharing** — Serve or statically export the pt2 atlas with documented collaborator access. [REQ-07]
- [ ] **Phase 6: Generalize to full cohort (15 ST samples; 6 with matched SM)** — Sample selector over all 15 ST samples; MS layer for the 6 matched (ven1–ven6), cleanly absent for the 9 ST-only. [REQ-08, REQ-09, REQ-10, REQ-11]

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
  3. Gene and Metabolite are presented as separate labelled panels (done: independent obsType/featureType scopes).
  4. A **sample selector** sits alongside the z slider (spans samples; see Phase 6 for cohort-wide data).
**Plans**: TBD at plan-time (est. 1–2)

### Phase 5: Deployment & sharing
**Goal**: Collaborators can open the pt2 atlas with documented steps.
**Depends on**: Phase 4
**Requirements**: REQ-07
**Success Criteria** (what must be TRUE):
  1. The atlas is served (or statically exported) and reachable by a second user following written instructions.
  2. Data-serving approach (static files vs http server, HPC port-forward vs export) is decided and documented.
**Plans**: TBD at plan-time (est. 1)

### Phase 6: Generalize to full cohort (15 ST samples; 6 with matched SM)
**Goal**: Every cohort sample browsable in one viewer, with the metabolite layer
present only where MS data exists.
**Depends on**: Phase 5
**Requirements**: REQ-08, REQ-09, REQ-10, REQ-11, REQ-Q4

**CORRECTED COVERAGE (verified 2026-07-20)** — earlier notes said SM was pt2/pt5
only; that was based on `integrated/*.rds`. The aligned MS matrices actually exist
for **all six ven samples**:

| Samples | ST | SM (metabolomics) | Source |
|---|---|---|---|
| ven1–ven6 (6) | yes | **yes** | `venture_pt{1..6}/metabolomics_edge_removed/*_with_xy.csv`, pt2 also `aligned_metabolites/` |
| GL0018, GL0043, GL0048, GL0097, GL0184, GX008, LGG-A/B/C (9) | yes | no | ST only |

**Success Criteria** (what must be TRUE):
  1. A generated **manifest** (sample → z-planes → modalities present) drives the
     selector; no hard-coded sample lists.
  2. The **sample selector** lists all 15 ST samples; picking one loads its planes.
  3. For the 6 matched samples the Metabolite (MS ion-density) panel appears; for
     the 9 ST-only samples it is cleanly omitted and the layout reflows (no dead panel).
  4. Per-sample MS alignment is validated (nearest-neighbour distance to cells)
     and recorded, as done for ven2 z1–z3.
  5. Root `.planning/` and semantic `results/` byte-unchanged.
**Plans**: TBD at plan-time (est. 3–4)

## Progress

| Phase | Plans | Status |
|-------|-------|--------|
| 1. Pipeline bootstrap | 1/1 | **Complete** (2026-07-20) |
| 2. pt2 AnnData assembly | 2/2 | **Complete** (2026-07-20) — 8 z-plane h5ad, genes+metab+celltype+niche |
| 3. webatlas config + build | done | **Complete** (2026-07-20) — 8-z spatial atlas; multimodal split proven |
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

---

## Milestone 2 — Production viewer

**Goal:** move from the working proof-of-concept to something comparable to
[gbmspace.org](https://www.gbmspace.org/) (which uses **WebAtlas 2.0** + CELLxGENE)
and [cellatlas.io webatlas viewer](https://cellatlas.io/studies/webatlas/dataset/140/vitessce)
(which runs the **webatlas-app** frontend).

**Gap analysis vs those targets (current state = points-only scatterplots in a raw
vitessce.io iframe):**

| Capability | Target has | We have | Phase |
|---|---|---|---|
| Frontend app w/ study+dataset browser | webatlas-app | raw vitessce.io iframe | 7 |
| Raster tissue image (H&E / IF) | yes | none | 8 |
| Cell segmentation polygons | yes | centroid points only | 8 |
| Histopath / region annotations | yes | niche only | 9 |
| Sample selector across cohort | yes | z-slider, 1 sample | 6 |
| Curated / manuscript-figure views | yes | none | 9 |
| Side-by-side comparison | yes | none | 9 |
| Hosting at cohort scale | CDN/object store | GitHub Pages (708MB for 3 planes) | 10 |

- [ ] **Phase 7: Self-hosted webatlas-app frontend** — deploy webatlas-app; study/dataset browser; replaces the iframe. [REQ-12, REQ-18]
- [ ] **Phase 8: Image + segmentation layers** — H&E/IF as OME-Zarr raster; cell polygons as label images (also unlocks webatlas's native spatial view). [REQ-13, REQ-14]
- [ ] **Phase 9: Annotations, curated views, comparison mode** — histopath/region layer; named figure presets; linked side-by-side. [REQ-15, REQ-16, REQ-17]
- [ ] **Phase 10: Object-storage hosting** — R2/S3 + CORS; retire the Pages size ceiling. [REQ-19]

**Sequencing note:** Phase 10 (hosting) gates 6-9 in practice — the cohort will not
fit on Pages. Phase 8 is the biggest visual win (tissue context + real cell shapes).
