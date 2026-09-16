# Phase 6 — store efficiency: what the cohort actually costs

Measured from the live pilot store `lgg_pt2_atlas-ven2_z1-anndata.zarr`
(40,107 cells), not estimated.

## What is in a cells store today

| Array | Shape | dtype | Used by the viewer? |
|---|---|---|---|
| `X` | 40107 × 1196 | **`<f8`** (float64) | **yes** — the feature matrix |
| `obsm/spatial` | 40107 × 2 | `<i4` | **yes** — the scatterplot |
| `obsm/X_umap` | 40107 × 2 | `<f4` | yes (UMAP view) |
| `obsm/spatial_aligned` | 40107 × 2 | `<f4` | no |
| `obsm/X_pca` | 40107 × 50 | `<f4` | **no** |
| `obsp/connectivities` | 857,732 nnz | `<f4`/`<i4` | **no** |
| `obsp/distances` | 561,498 nnz | **`<f8`** | **no** |
| `obs/cell_type`, `obs/niche` | categorical | `\|i1` | yes |
| `obs/_index`, `obs/cell_id`, `obs/cellname` | 3 string columns | `\|O` | one of them |

`X` has 1196 columns because genes and metabolites are **fused into one matrix**
(339 genes + 857 m/z), with `var/is_gene` used as the feature filter. ST-only
samples will therefore have a much narrower `X` (339 columns), and are
proportionally cheaper.

## The dominant cost, and the one lever that matters

`X` is float64. At 40,107 × 1196 that is **384 MB raw**, compressing to the
~127 MB observed on disk — i.e. `X` *is* the store; everything else is rounding.

**Storing `X` as float32 halves the entire atlas.** Expression counts and ion
intensities do not carry sixteen significant figures; float64 is an artefact of
numpy defaults, not a requirement. Applied cohort-wide this is the difference
between roughly **22 GB and 11 GB** — and because chunks are fetched per feature
selection, it halves the bytes a reviewer pulls per interaction too, which is a
direct mitigation for the 1 GB/core/month off-net quota.

Note this does **not** conflict with the hard-won "X must be DENSE" rule (sparse
CSR triggers `LoaderNotFoundError`). Dense float32 is still dense.

## Free savings

- **Drop `obsp/`** (`connectivities`, `distances`) — scanpy kNN graph leftovers
  the viewer never reads. `distances` is float64 for no reason.
- **Drop `obsm/X_pca`** — unused by any view.
- **Drop `obsm/spatial_aligned`** if the configs reference only `obsm/spatial`.
- **Collapse the redundant string columns** — `_index`, `cell_id` and `cellname`
  are three `|O` arrays where the viewer needs one identifier.

Individually these are ~10–25 MB per plane; together with the float32 change they
make the difference between a cohort that fits comfortably and one that needs a
storage conversation.

## Chunking, and a responsiveness trade-off

`X` is chunked `[40107, 10]` — all cells × 10 features. Selecting a single gene
therefore fetches a chunk containing **ten** features: the smoke test measured
1.7 MB transferred to read one gene.

Finer feature chunking (`[n_cells, 1]`) would fetch exactly the selected feature,
cutting per-interaction bytes ~10x, at the cost of 1196 chunk objects per store
instead of 120 — which multiplies the cohort object count by roughly the same
factor and makes rsync slower.

**Recommendation:** try an intermediate (e.g. `[n_cells, 4]`) and measure, rather
than assuming. The object-count budget and the per-interaction byte budget pull in
opposite directions here, and the off-net quota makes the byte side worth more
than it would normally be. Decide with numbers from one rebuilt sample before
committing the cohort.

## Implication for the allocation request

The 100 GB volume already requested stays right — it was deliberately
conservative, and these savings only widen the headroom that Phase 8's tissue
image layers will later consume. No change needed to the submitted numbers.

---

*Phase 6 — companion to `06-SCOPE.md` and `06-VIEWER-ARCHITECTURE.md`.*
