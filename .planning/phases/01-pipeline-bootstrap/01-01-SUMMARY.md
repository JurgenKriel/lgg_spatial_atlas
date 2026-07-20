# Phase 1 — SUMMARY (2026-07-20)

**Status: COMPLETE** (Task 3 browser-view is the only manual step — needs a user port-forward).

## What was built
- Cloned **webatlas-pipeline v0.5.3** (commit a9b9d5d) → `webatlas/webatlas-pipeline/` (gitignored).
- Pinned toolchain in `webatlas/versions.env`: Nextflow 25.10.3, apptainer/1.4.1,
  containers `haniffalab/webatlas-pipeline:0.5.2` + `build-config:0.5.2`, Java 17.
- Pulled both containers (996M + 577M) to `NXF_SINGULARITY_CACHEDIR` (scratch).
- `webatlas/PIPELINE_CONTRACT.md` — the AnnData/params contract, now CONFIRMED against a real run.
- Smoke test: `make_smoke_anndata.py` (200-cell synthetic) + `smoke/smoke_params.yaml`
  + `run_example.sh` + `smoke/extra.config`.

## Verified (smoke run, exit clean)
- Pipeline runs end to end under apptainer → AnnData-zarr + **Vitessce config.json (v1.0.15)**.
- Output is **zarr v2** — compatible with local envs, no down-conversion.
- **Gene** (obsFeatureMatrix=X), **Cell type** + **Niche** (obsSets) selectors all wired.
- Embeddings (X_pca/X_umap) auto-computed from `compute_embeddings: True`.

## Key learnings for Phase 2/3
1. **numba cache gotcha (blocking):** read-only container + `import scanpy` fails numba
   caching. MUST run with `-c smoke/extra.config` (sets NUMBA_CACHE_DIR/MPLCONFIGDIR to
   /tmp). Host env passthrough does not reach the container.
2. **Metabolite = 4th selector** needs the multimodal path (2nd feature matrix) — the
   single-modality Full_pipeline gives us 3 of 4. Target multimodal in Phase 3.
3. Nextflow 25.10 parses the 2023-era DSL2 with a harmless lexer warning; no downgrade needed.

## Remaining manual step (Task 3)
Browser view needs a port-forward (interactive):
`bash webatlas/serve_view.sh` on the node, then from laptop
`ssh -L 3000:localhost:3000 <you>@il-n03...`, open
`https://vitessce.io/#?url=http://localhost:3000/lgg_atlas_smoke-smoke-config.json`.
