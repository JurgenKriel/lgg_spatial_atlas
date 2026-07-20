# ST ↔ MS z-plane mapping (ven2) — RESOLVED

## Conclusion
The **MS files were numbered correctly**. The error was in the **ST/cell plane
labels**: the cell h5ads built as `z1` and `z2` are swapped relative to the real
section order. Once the cell labels are corrected, each plane pairs with its
**same-numbered** MS file.

| Viewer plane (true) | cells zarr file | MS zarr file |
|---|---|---|
| z1 | `...ven2_z2-anndata.zarr` | `ms_ven2_z1` |
| z2 | `...ven2_z1-anndata.zarr` | `ms_ven2_z2` |
| z3 | `...ven2_z3-anndata.zarr` | `ms_ven2_z3` |

(zarr filenames keep their build-time names; the *config* does the cross-reference.)

## How we got here
1. User reported SM z1 matched ST z2.
2. Footprint Jaccard over all 8×8 pairs confirmed `MS_z1 ↔ ST_z2` as a mutual best
   match (.741 vs .52–.59 elsewhere). All other pairs sat at .70–.83 — **not
   resolvable** by footprint, since every plane is the same tissue block.
3. First fix cross-referenced the MS files (ST z1→MS z2). Sections then matched,
   but the user identified the **labels** as inverted — i.e. the cell planes, not
   the MS files, carried the wrong z numbers.

## Root cause of the bad cell labels
The ST z-numbers came from mapping the integrated object's `sample_id`
(6901_1/6901_2/…) onto `ven2_z*` via cell_id overlap with
`venture_ST/full_ven_cohort_annotations.csv`. The cell↔label assignment matched at
100%, so the inversion is in that z-numbering convention itself (or it differs from
the section order used at the bench), not in the join.

## Open risk
- **z3–z8 pairings are UNVERIFIED.** Footprint overlap cannot resolve them.
- Before publishing further planes, confirm each visually, or use a stronger
  discriminator (a metabolite correlated with a colocalised gene/cell-type signal,
  or an independent per-section registration record).
- The same z-label inversion may affect z4–z8; do not assume z_N ↔ z_N there.
