# webatlas-pipeline I/O Contract (v0.5.3)

Derived from the cloned source at `webatlas-pipeline/` (tag v0.5.3,
commit a9b9d5d) on 2026-07-20. This is the spec Phase 2 (AnnData build) and
Phase 3 (config) must target.

## Two entry points

| Entry | File | Config schema | Use for us |
|-------|------|---------------|-----------|
| `Full_pipeline` | `main.nf` | `projects → datasets → data[] (data_type/data_path)` + top-level `vitessce_options` | Single-modality per dataset; simplest |
| Multimodal | `multimodal.nf` + `bin/build_config_multimodal.py` | `data[]` list, each with `anndata` (zarr), `obs_type`, `offset`, `is_spatial`, `extend_feature`, per-dataset `vitessce_options` | **Our path** — combine gene + metabolite feature types in one view |

Run:
```
nextflow run main.nf       -params-file <yaml> -entry Full_pipeline -profile singularity
nextflow run multimodal.nf -params-file <yaml>                      -profile singularity
```

## Full_pipeline params schema (templates/template.yaml)
```yaml
outdir: "/path/out/"
args:
  h5ad:
    compute_embeddings: "True"   # computes X_pca / X_umap if absent (bin/process_h5ad.py:preprocess_anndata)
    batch_processing: "True"
projects:
  - project: <name>
    datasets:
      - dataset: <name>
        title: "..."
        data:
          - { data_type: h5ad,        data_path: /.../anndata.h5ad }
          - { data_type: raw_image,   data_path: /.../raw_image.tif }      # optional
          - { data_type: label_image, data_path: /.../label_image.tif }    # optional; we have NONE (points only)
vitessce_options:
  spatial: { xy: "obsm/spatial" }
  mappings: { obsm/X_umap: [0, 1] }
  factors: [ "obs/celltype" ]      # metadata shown per cell
  sets:    [ "obs/celltype" ]      # obsSets selector (categorical) -> our cell_type + niche
  matrix: "X"                      # feature matrix (genes)
layout: "simple"                   # or minimal / advanced / custom_layout string
```

## Multimodal params schema (templates/multimodal-template.yaml)
```yaml
url: http://localhost/
project: <name>
title: "..."
outdir: ./output/
data:
  - dataset: <name>
    obs_type: "cell"                 # coordination unit; multiple obs_types allowed
    anndata: <sample>.zarr           # AnnData written to zarr (process_h5ad converts h5ad->zarr)
    offset: 0                        # obs-id offset so datasets don't collide (use 0, 1e6, 2e6...)
    is_spatial: true
    label_image: <...>.zarr          # optional
    extend_feature: obs/celltype     # optional: extend matrix by a derived feature
    vitessce_options:
      spatial: { xy: "obsm/spatial" }
      mappings: { obsm/X_umap: [0, 1] }
      factors: [ "obs/celltype" ]
      sets:    [ "obs/celltype", "obs/niche" ]
      matrix: "X"                    # -> OBS_FEATURE_MATRIX path; can be a layer path e.g. "layers/metabolites"
```

## AnnData expectations (bin/process_h5ad.py)
- **Spatial coords:** read from `obsm/spatial` (key set by `vitessce_options.spatial.xy`).
  Cast to int32 during preprocessing. -> put centroids here.
- **Expression matrix:** `X` by default (or a `layers/<name>` path via `matrix`).
- **obs categoricals:** exposed via `sets`/`factors` as `obs/<col>`. bool -> str->category;
  int8/int64 -> int32. -> `obs/cell_type`, `obs/niche`.
- **Embeddings:** `obsm/X_umap`, `obsm/X_pca`; auto-computed if `compute_embeddings: True`.
- **obs index** is reindexed to integer codes+1 (`reindex_anndata_obs`); `offset` added in multimodal.
- Output is written to **zarr** (AnnData-zarr) consumed by Vitessce.

## Metabolites as a distinct selectable feature type — RESOLVED (Risk #2)
`bin/build_config_multimodal.py` (lines ~124-126) explicitly supports **multiple
feature matrices**: "if 2+ featureTypes (e.g. genes + celltypes) then 1 + n ×
OBS_FEATURE_MATRIX_ANNDATA_ZARR". So **Gene and Metabolite can each be a separate
Vitessce feature type**, either:
  - **(A)** one AnnData with genes in `X` and metabolites in `layers/metabolites`,
    exposing two matrix paths, OR
  - **(B)** two multimodal `data[]` datasets (genes, metabolites) sharing obs_type
    "cell" with matched `offset`.
Recommendation: start with **(A)** (one AnnData per sample/z-plane, metabolites as
a layer) — simplest join, one obs table. Confirm the exact multi-matrix option
wiring when authoring the Phase 3 config (the builder reads `options.matrix`; a
second featureType is added when the config lists more than one).

## Containers (nextflow.config)
- singularity profile runtime image: `docker://haniffalab/webatlas-pipeline:0.5.2`
- build_config image: `docker://haniffalab/webatlas-pipeline-build-config:0.5.2`
- Pulled to `NXF_SINGULARITY_CACHEDIR=/vast/scratch/users/kriel.j/singularity_cache`
- Engine: apptainer/1.4.1 (module), `singularity.autoMounts = true`

## Output zarr version
Pipeline writes AnnData-zarr + OME-Zarr via its pinned container deps (zarr-python
2.x era, 0.5.2 image). Expected **zarr v2** — compatible with local envs. Verify the
`.zarray`/`zarr_format` of the example output; down-convert only if v3 appears
(scripts/convert_zarr_v3_to_v2.py).

## Notes / gotchas
- We have **no label images** (cells are centroid points). Omit `label_image`;
  Vitessce renders spots from `obsm/spatial`. Cell-boundary polygons are a later
  enhancement.
- v0.5.3 tag pins the *singularity* runtime container to 0.5.2 (docker to 0.5.3) —
  intentional per nextflow.config; use 0.5.2 for apptainer.
- Nextflow 25.10.3 (~/bin) is far newer than the pipeline (2023-era). If DSL2/syntax
  incompat surfaces, fall back to `module load nextflow/24.10.5` or `23.10.0`.

---

## Phase 1 smoke-run findings — CONFIRMED (2026-07-20)

Ran `Full_pipeline` on a 200-cell synthetic AnnData under apptainer/1.4.1 +
Nextflow 25.10.3. Outputs in `/vast/scratch/users/kriel.j/webatlas_smoke_out/0.5.3/`.

- **Works end to end.** Processes: `Process_files:route_file` (h5ad→zarr) +
  `Output_to_config:Build_config` (→ Vitessce config.json).
- **Output zarr is v2** (`.zgroup` → `"zarr_format": 2`). No down-conversion needed;
  local envs read it directly.
- **Vitessce config schema v1.0.15.** Real field names produced from our
  `vitessce_options`:
  - `obsLocations.path = obsm/spatial`  (from `spatial.xy`)
  - `obsEmbedding[].path = obsm/X_umap` (auto-computed by `compute_embeddings: True`; also writes X_pca)
  - `obsSets[] = obs/cell_type, obs/niche`  (from `sets`)  → **Cell type + Niche selectors**
  - `obsLabels[] = obs/cell_type, obs/niche` (from `factors`)
  - `obsFeatureMatrix.path = X`  (from `matrix`)  → **Gene selector**
- So **3 of our 4 layers (Gene, Cell type, Niche) work with the single-modality
  Full_pipeline**. **Metabolite** needs the multimodal path / a 2nd feature matrix
  (see "Metabolites as a distinct feature type" above) — target that in Phase 3.

### HPC gotcha (REQUIRED for every run) — numba/matplotlib cache
The container fs is read-only; `import scanpy` triggers numba caching which fails
with `cannot cache function ... no locator available`. Fix via a Nextflow `env {}`
override (`smoke/extra.config`) — host env passthrough (`APPTAINERENV_*`) does NOT
reach the container:
```groovy
env { NUMBA_CACHE_DIR='/tmp/numba_cache'; MPLCONFIGDIR='/tmp/mpl_cache'; XDG_CACHE_HOME='/tmp/xdg_cache' }
process { beforeScript = 'mkdir -p /tmp/numba_cache /tmp/mpl_cache /tmp/xdg_cache' }
```
Pass with `-c smoke/extra.config`. Reuse this config for the real pt2 runs.

### Container naming note
Nextflow re-pulls with its own cache filename (`haniffalab-webatlas-pipeline-0.5.2.img`),
ignoring manually-named `.sif`. The manual `pull_containers.sh` still helps by warming
the OCI layer cache. Both live in `NXF_SINGULARITY_CACHEDIR`.
