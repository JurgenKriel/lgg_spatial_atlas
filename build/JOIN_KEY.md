# pt2 Cell Join — RESOLVED (Phase 2, 02-01) 2026-07-20

## Headline
The three-way join collapses to a **single source + one niche join**, and it is
**exact (100% matched)**.

## Sources (final)
- **`venture_pt2/integrated/integrated_data_250925.rds`** (Seurat) — the pt2
  integrated ST+metabolomics object, already fused on shared cells:
  - assay **`SPT`** = 339 Xenium genes
  - assay **`SPM`** = 857 metabolites (m/z, e.g. `mz-72.0800762176514`)
  - 334,395 cells across 8 sample_ids; `Anno` (23 cell types), `cell_id`,
    `x_centroid/y_centroid`, `x_aligned/y_aligned`, 8 spatial images, embeddings
    (spm.umap, integrated.umap, wnn.umap, …).
  - cell name = `<sample_id>_<cell_id>`, e.g. `6901_1_aahoahif-1`; `cell_id`
    column is the bare Xenium barcode `aahoahif-1`.
- **`venture_ST/full_ven_cohort_annotations.csv`** (patient==`ven2`, 358,471 rows)
  — source of **`niche`** (not present in the integrated object). Key: bare
  `cell_id` + `sample` (`ven2_z1..z8`). (sample,cell_id) is unique.

NOTE: the cohort Seurat `ven_all_250217.rds` is **NOT needed** for pt2 — the
integrated object already carries the measured 339-gene SPT assay. (The 15k
imputed gene set is a separate object used for pathway work, not the atlas.)

## Join key & sample mapping
Key = (sample, `cell_id`). Integrated `sample_id` maps 1:1 to CSV `ven2_z*` by
cell_id overlap (**100% each**), in reversed z-order:

| integrated sample_id | ven2 z-plane | cells |
|---|---|---|
| 6901_2 | ven2_z1 | 40107 |
| 6901_1 | ven2_z2 | 31386 |
| 6889_2 | ven2_z3 | 47450 |
| 6889_1 | ven2_z4 | 42513 |
| 6694_2 | ven2_z5 | 39834 |
| 6694_1 | ven2_z6 | 42565 |
| 6687_2 | ven2_z7 | 42032 |
| 6687_1 | ven2_z8 | 48508 |

## Matched fraction (the gate)
- **niche joined for 334,395 / 334,395 = 100.00%** of integrated cells. PASS
  (threshold was ≥0.8).
- Cross-check: integrated `Anno` vs CSV `celltype` agree on **99.5%** of matched
  cells → same cells, consistent labels.

## Consequence for 02-02 (build)
One AnnData per z-plane (8 total for pt2):
- `X` = SPT genes (feature_type=gene); metabolites SPM as a 2nd matrix/layer
  (feature_type=metabolite) — enables the 4th (Metabolite) Vitessce selector.
- `obs.cell_type` = Anno; `obs.niche` = joined niche; `obsm['spatial']` =
  x_centroid/y_centroid (also keep x_aligned/y_aligned).
- palettes: Anno_color/niche_color carried to `uns`.
