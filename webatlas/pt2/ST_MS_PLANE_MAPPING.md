# ST ↔ MS z-plane mapping (ven2)

The MS aligned-metabolite files are labelled on a different z convention than the
ST/cell planes. Reported by the user and confirmed empirically.

## Evidence
Tissue-footprint Jaccard overlap (60u grid, MS spots vs cell centroids), all 8×8:
most pairs sit at 0.70–0.83 because every plane is the same tissue block — i.e.
**footprint overlap cannot resolve most pairings**. One signal is unambiguous:

    MS_z1:  ST_z1=.544  ST_z2=.741  ST_z3=.519 ... ST_z8=.525

`MS_z1` ↔ `ST_z2` is a mutual best match (the ST_z2 column is low for every other
MS plane). This confirms the reported offset.

## Mapping applied (viewer configs)
| ST / cell plane | MS file used |
|---|---|
| ST z1 | `Ven2B_z2_transformed_metabolite_matrix_final.txt` (→ `ms_ven2_z2` zarr) |
| ST z2 | `z1_met_final.txt` (→ `ms_ven2_z1` zarr) |
| ST z3 | `Ven2C_z3_...final.txt` (→ `ms_ven2_z3` zarr) — **UNVERIFIED** |

NOTE: zarr filenames keep the MS-file naming; the *config* does the cross-reference.

## Status / caution
- ST z1 ↔ MS z2 and ST z2 ↔ MS z1: applied per user report; the MS_z1↔ST_z2 half
  is statistically confirmed.
- **ST z3 and beyond are NOT verified.** Footprint overlap is too degenerate to
  resolve them. Before publishing more planes, confirm each pairing visually, or
  find a stronger discriminator (e.g. correlating a metabolite with a colocalised
  gene/cell-type signal, or an independent per-section registration record).
