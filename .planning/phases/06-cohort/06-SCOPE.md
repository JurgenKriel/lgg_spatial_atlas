# Phase 6 — cohort atlas: scope

What it takes to go from the one-patient pilot to the full cohort, grounded in a
data inventory done 2026-09-16 rather than in the roadmap's assumptions. Several
of those assumptions were wrong; the corrections are in §1 and they change the
shape of the work.

Companions: `06-VIEWER-ARCHITECTURE.md` (settled design), `06-STORE-EFFICIENCY.md`
(what the cohort costs).

---

## 1. The cohort is not what the roadmap says

The roadmap describes "15 ST samples × 8 z-planes, 6 with matched SM". Three
parts of that are wrong, and one of them is a correctness problem rather than a
counting problem.

### 1.1 There are two axes, not one

| Group | Patients | Shape | Axis |
|---|---|---|---|
| ven series | ven1–ven6 | serial z-stack of one block (ven2/3/4/6 × 8, ven1 × 2, ven5 × 8 + 2) | **depth** |
| GL / GX / LGG | 9 patients | flat 2D sections, one per clinical timepoint | **time** |

The nine non-ven patients are **not z-stacks**. Their extra sections are
different clinical timepoints — primary versus recurrent, split by treatment
(`recurrent_nil`, `recurrent_rt`, `recurrent_tmz_bev`, `recurrent_tmz_rt`,
`recurrent_safu`, `recurrent_vora`) — and in several cases a different specimen
entirely. GX0008 alone is a primary plus three differently-treated recurrences.

`export_centroids_to_spatialdata.py` collapses this by filling `z_layer = "z0"`
for any sample not matching `_z<N>$`, which throws the distinction away. Had we
built the cohort atlas on that, **the viewer would have presented a recurrent
tumour as "another z-plane" of the primary** — a scientific misstatement, not a
cosmetic one. A depth slider between two specimens implies a spatial continuity
that does not exist.

**Resolved in this phase:** `build/make_sections_table.py` recovers the
distinction from the cohort annotations CSV, and the manifest and viewer carry an
`axis` per patient — a slider for depth, a labelled list for timepoints.

### 1.2 The real counts

Measured from `venture_ST/full_ven_cohort_annotations.csv` (7,148,072 rows):

**66 sections across 15 patients; 7.15M cells.** Six patients have a z-stack.
ven5 is genuinely mixed (an 8-plane stack plus two later `recurrent_vora`
sections), so "mixed" is a real axis value, not a defect.

Per-patient cell counts range from 126k (GL0184) to 1.33M (ven3). ven3 alone has
more cells than the entire pt2 pilot by a factor of four.

### 1.3 Metabolomics coverage is thinner and messier than recorded

The roadmap says all six ven samples have matched MS. Actually:

| Patient | MS planes | Format | State |
|---|---|---|---|
| ven1 | **2 only** | `metabolomics_edge_removed` | hard data limit, not a path problem |
| ven2 | 8 | `aligned_metabolites/layer_{1..8}/` | **aligned**, `x_transformed`/`y_transformed` present |
| ven3–ven6 | 8 each | `metabolomics_edge_removed` | **raw, pre-alignment** — only `x`,`y` |

This is the single largest blocker (§3.1). pt2 is the only patient with a clean,
canonical, ST-frame-aligned file per plane. For ven3–ven6 the aligned outputs are
scattered across `final_aligned/`, `aligned_lddmm/`, `aligned_lddmm_2/`,
`aligned_coordinates/` — 11–24 GB per patient of versioned attempts
(`iter_500/800/1000/5000`, `_shifted`, `_update`, `_2/_3/_4`) with no marker for
which is canonical.

### 1.4 Other corrections

- **The gene panel is 307 genes, not 339.** Confirmed two ways (the measured
  `spatial_counts*.txt` header, and the cohort SCE's `dim`). The pilot's 339
  figure appears to be a different panel version or an imputed matrix.
- **Centroids stores are healthy.** All 30 were regenerated 2026-08-21; the
  "29 emptied" incident is closed. Not a blocker.
- **`white` is a bogus niche category** present across samples (pt2 and GL0184
  both), with no biological identity. It should be filtered or renamed at build
  time, not shown in a legend.
- **Names do not match across sources**: the CSV says `GX008`/`LGGA`; the stores
  say `GX0008`/`LGG-A1`. `make_sections_table.py` is now the normaliser.

---

## 2. What is already built

Done and tested against real data in this phase:

| Component | State |
|---|---|
| `build/make_sections_table.py` | Derives 66 sections, two axes, treatment labels, grades, cell counts from the cohort CSV in ~23 s. Also the naming normaliser. |
| `build/niche_key.json` | Canonical 12-niche code → display → biological identity, in the repo rather than in someone's head. |
| `deploy/make_manifest.py` | Schema 3: patients → sections, per-patient `axis`/`grade`/`modalities`, cohort legend with identities, per-section cell counts. |
| `app/` viewer | Patient selector; depth slider **or** timepoint list per axis; ST-only layout; niche key with identities; URL state (`?patient=&section=`) for deep links. |
| `webatlas/build_config_v8.py` | MS now optional — ST-only samples get a full-width panel, not a dead one. Names derived from the section instead of the literal `ven2_z1` every config previously carried. |
| `deploy/smoke_test.sh` | Schema-3 aware; fails rather than skips when it cannot check. |

Verified end to end: a two-patient release (ven2 z-stack + GL0018 timepoint,
mixed modalities) served through real nginx passes **16/16** checks, including
every data URL across all four configs resolving.

---

## 3. Blockers — these need decisions, not code

### 3.1 Which MS file is canonical for ven3–ven6? *(blocks the MS layer for 4 patients)*

Someone who knows the alignment work — moffet.j or lu.t — must name, per patient
per plane, the one ST-frame-aligned coordinate file. Until then the cohort atlas
can ship **ven2's 8 MS planes and ven1's 2**, and the other four ven patients are
ST-only in the viewer. That is a perfectly shippable first cohort release, and it
is the recommended path rather than blocking everything on an alignment cleanup.

### 3.2 Which cohort gene-expression object is canonical?

Two candidates sit side by side on stornext: `ven_all_250217.rds` (1.17 GB,
2025-03) and `full_ven_integrated_cleaned.rds` (a SingleCellExperiment,
307 genes × 7.06M cells, 2026-05 — newer). Their per-sample coverage is
unverified. Needs moffet.j to confirm, plus a header-only probe job rather than
loading either blind. Note stornext is read-only on login nodes: any copy runs on
the `datamover` partition.

### 3.3 pt6 z4 has two unreconciled files

`Ven6D_..._with_xy.csv` (lu.t, Jan) and `..._with_xy2.csv` (moffet.j, Feb): same
row and column counts, every field in a different position. Needs an owner call.

### 3.4 The z-plane pairing risk is now resolvable — and should be resolved

`ST_MS_PLANE_MAPPING.md` records that pt2's cell planes z1/z2 were swapped and
that **z3–z8 pairings are UNVERIFIED**, because footprint overlap cannot separate
planes of the same block. The independent registration record it asked for
exists: the per-section `z_centroid` depths recorded for pt2's eight Xenium
sections are 70, 10, 190, 130, 250, 310, 370, 430 µm — **not monotonic in the
z label**. That is exactly the reported z1/z2 inversion, and it says the same
inversion applies to z3/z4, while z5–z8 are already in depth order.

This should be confirmed and applied before publishing further planes, and
before the same convention is applied 66 times. Shipping unverified pairings
across the cohort would multiply a known error.

---

## 4. Remaining build work

Ordered by what unblocks what. The audit found the pipeline is parameterised
almost nowhere; most of this is threading arguments through.

1. **Cohort palette** — one union palette over all samples, replacing per-sample
   `uns` colours. Without it the same cell type takes different colours in
   different patients. Filter `white` here.
2. **Parameterise the build scripts** — `export_pt2_matrices.R` and
   `build_pt2_anndata.py` have zero arguments; the sample→z map is a literal
   dict, hand-transcribed from a script that only prints to stdout. Make
   `validate_join.py` emit that mapping as a file and consume it.
3. **Fix the shared-state collisions** before any parallel run:
   `run_pt2_multimodal.sh` has a fixed Nextflow work directory (two samples race
   and corrupt both); `export_pt2_matrices.R` writes unqualified
   `SPT_genes.txt`/`SPM_metabolites.txt` into one shared directory.
4. **Slim the stores** — float32 instead of float64 for `X` halves the atlas and
   halves per-interaction egress; drop unused `obsp/` and `obsm/X_pca`. See
   `06-STORE-EFFICIENCY.md`.
5. **Cohort driver** — a SLURM array over the 66 sections with per-section output
   paths, writing into one release directory using the filename convention the
   manifest keys off.
6. **Resolve the `var/is_gene` mismatch** — the config builder filters on
   `var/is_gene`, but the AnnData builders write `feature_type`/`is_metabolite`.
   It currently works only because the Nextflow step adds `is_gene`. Make that
   dependency explicit or the first build that skips the pipeline step breaks.

---

## 5. Sizing

The pilot measures 708 MB / 1,404 objects for three planes of one patient. The
cohort is 66 sections and 7.15M cells, but composition varies: ST-only sections
carry 307 gene columns against the pilot's 1,196 fused columns, so they are far
cheaper per cell.

Order of magnitude **~20 GB at float64, ~10 GB at float32**, with ven3/ven4/ven6
dominating on cell count. The 100 GB volume in the allocation request stands with
comfortable headroom — which Phase 8's tissue rasters will consume, not this.

---

## 6. Recommended first cohort release

Do not wait for §3.1. Ship:

- all 66 sections with cells, cell type, niche and gene expression;
- the MS layer for **ven2 (8 planes) and ven1 (2)** only;
- ven3–ven6 as ST-only until their canonical aligned file is named;
- z3–z8 pairings applied only after §3.4 is confirmed.

That is a complete, honest cohort atlas that no longer depends on anyone else's
calendar, and the MS layer for four more patients drops in later as a data
change with no code change — the manifest already carries per-section modality.

---

*Phase 6 — scope, 2026-09-16.*
