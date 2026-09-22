"""Per-plane metabolite annotation lookup for ven2-ven6 MS layers.

Source: Ven2_Ven3_Ven4_Ven5_Ven6_selected_peak_annotation.csv (428 rows, two blocks):
  * HMDB block (ID set, 119 rows): peaks common to all 40 planes, one row per HMDB
    candidate annotation; 29 rows also carry a targeted-panel hit in
    candidate_metabolite_names / candidate_adduct_matches.
  * targeted block (ID NaN, 309 rows): targeted panel metabolite x adduct queries
    (glucose, glutamine, citrate, ...); IsomerNames is the metabolite.
Columns Ven{N}{A..H} hold the peak's observed m/z in each plane ("nah" = absent),
which match the MS matrix column m/z exactly (float32 rounding, <2e-5). Plane
letters map A..H -> z1..z8 (same as aligned_metabolites/Ven2B_z2..., verified for
ven2 z1-z3 by unique m/z match).

Usage:
  python metabolite_annotations.py <annotation.csv> <out.tsv>
  from metabolite_annotations import annotate_var   # used by build_ms_layers.py
"""
import re, sys
import numpy as np, pandas as pd

SAMPLES = ["Ven2", "Ven3", "Ven4", "Ven5", "Ven6"]
PLANES = "ABCDEFGH"
MZ_TOL = 5e-5          # observed m/z in csv vs matrix column (float32 round-off ~1.5e-5)
DEFAULT_TSV = __file__.rsplit("/", 1)[0] + "/metabolite_annotations_ven2-6.tsv"


def _ppm(obs, ref):
    return (obs - ref) / ref * 1e6


def _targeted_hits(row, panel):
    """(name, hmdb, adduct, ref_mz) targeted-panel hits carried on an HMDB-block row.
    Names are canonicalised via HMDB id to the targeted block's spelling
    (e.g. 'Serine_HMDB0000187' -> 'L-Serine')."""
    s = row["candidate_adduct_matches"]
    if not isinstance(s, str):
        return []
    hits = []
    for part in s.split(";"):
        name, adduct, ref = [p.strip() for p in part.split("|")]
        short, hmdb = re.match(r"(.+)_(HMDB\d+)$", name).groups()
        hits.append((panel.get(hmdb, short), hmdb, adduct, float(ref)))
    return hits


def build_table(csv):
    a = pd.read_csv(csv)
    tgt = a[a["ID"].isna()]
    panel = dict(zip(tgt["Isomers"], tgt["IsomerNames"]))   # HMDB id -> panel name
    recs = []
    for s in SAMPLES:
        for i, L in enumerate(PLANES):
            col = f"{s}{L}"
            obs = pd.to_numeric(a[col], errors="coerce")
            for idx, mz in obs.dropna().items():
                r = a.loc[idx]
                base = dict(sample=s.lower(), plane=L, z=f"z{i+1}", mz=float(mz),
                            cluster_mz=float(r["cluster_mz"]),
                            common_40_of_40=bool(r["common_40_of_40"]),
                            consistent_6of8=bool(r[f"consistent_6of8_{s}"]))
                if pd.isna(r["ID"]):   # targeted block
                    recs.append(dict(base, kind="targeted", name=r["IsomerNames"],
                                     adduct=r["Adduct"].strip(), formula=r["Formula"],
                                     hmdb=r["Isomers"], ref_mz=r["Reference_mz"]))
                else:                  # HMDB block (+ any targeted hit on the same peak)
                    recs.append(dict(base, kind="hmdb", name=r["IsomerNames"],
                                     adduct=r["Adduct"].strip(), formula=r["Formula"],
                                     hmdb=r["Isomers"], ref_mz=r["Reference_mz"]))
                    for name, hmdb, adduct, ref in _targeted_hits(r, panel):
                        recs.append(dict(base, kind="targeted", name=name, adduct=adduct,
                                         formula=None, hmdb=hmdb, ref_mz=ref))
    long = pd.DataFrame(recs)
    long["ppm"] = _ppm(long["mz"], long["ref_mz"])
    return long.groupby(["sample", "plane", "z", "mz"], sort=True).apply(_collapse, include_groups=False).reset_index()


def _collapse(g):
    """One annotation per (plane, peak): targeted-panel names win over HMDB candidates."""
    tg = g[g.kind == "targeted"].drop_duplicates(["name", "adduct"])
    hm = g[g.kind == "hmdb"]
    hm_names = list(dict.fromkeys(n.strip() for s in hm["name"] for n in s.split(";")))
    hm_ids = list(dict.fromkeys(n.strip() for s in hm["hmdb"].dropna() for n in s.split(";")))
    if len(tg):
        tg = tg.loc[tg["ppm"].abs().sort_values().index]
        name = " / ".join(dict.fromkeys(tg["name"]))
        adduct = " / ".join(tg["adduct"])
        ppm = tg["ppm"].iloc[0]
        source = "targeted+hmdb" if len(hm) else "targeted"
        tag = " / ".join(f"{n} [{a}]" for n, a in zip(tg["name"], tg["adduct"]))
    else:
        best = hm.loc[hm["ppm"].abs().idxmin()]
        name = best["name"].split(";")[0].strip()
        adduct, ppm, source = best["adduct"], best["ppm"], "hmdb"
        extra = len(hm_names) - 1
        tag = f"{name} [{adduct}]" + (f" (+{extra} alt)" if extra > 0 else "")
    mz = g.name[-1]
    return pd.Series(dict(
        label=f"{tag} · m/z {mz:.4f}", metabolite_name=name, adduct=adduct,
        ppm_error=round(float(ppm), 2), annotation_source=source,
        targeted_names="; ".join(dict.fromkeys(tg["name"])) if len(tg) else "",
        targeted_hmdb_ids="; ".join(dict.fromkeys(tg["hmdb"])) if len(tg) else "",
        hmdb_candidates="; ".join(hm_names), hmdb_ids="; ".join(hm_ids),
        n_hmdb_candidates=len(hm_names), cluster_mz=g["cluster_mz"].iloc[0],
        common_40_of_40=g["common_40_of_40"].iloc[0],
        consistent_6of8=g["consistent_6of8"].iloc[0]))


def annotate_var(var, sample, plane, table=None):
    """Return var with annotation columns and a readable, unique index.

    var needs a `raw_mz` column; sample e.g. 'ven2'; plane a letter (A..H) or 'z1'..'z8'.
    The old index is kept in var['mz_id'].
    """
    t = pd.read_csv(table or DEFAULT_TSV, sep="\t")
    key = "z" if str(plane).startswith("z") else "plane"
    t = t[(t["sample"] == sample.lower()) & (t[key] == plane)].sort_values("mz")
    var = var.copy()
    var["mz_id"] = var.index.astype(str)
    raw = var["raw_mz"].to_numpy(dtype=float)
    j = np.searchsorted(t["mz"].to_numpy(), raw)
    hit = np.full(len(raw), -1)
    for k, (m, jj) in enumerate(zip(raw, j)):
        for c in (jj - 1, jj):
            if 0 <= c < len(t) and abs(t["mz"].iat[c] - m) < MZ_TOL:
                hit[k] = c
    ok = hit >= 0
    missing = set(range(len(t))) - set(hit[ok])
    if missing:
        raise ValueError(f"{sample} {plane}: {len(missing)} annotated m/z not in matrix, "
                         f"e.g. {t['mz'].iloc[sorted(missing)[:3]].tolist()}")
    cols = ["metabolite_name", "adduct", "ppm_error", "annotation_source",
            "targeted_names", "targeted_hmdb_ids", "hmdb_candidates", "hmdb_ids", "n_hmdb_candidates"]
    for c in cols:
        vals = t[c].to_numpy()[hit.clip(0)]
        if t[c].dtype.kind in "if":
            var[c] = np.where(ok, vals, np.nan)
        else:
            var[c] = np.where(ok, pd.Series(vals).fillna("").astype(str), "")
    var["is_annotated"] = ok
    labels = np.where(ok, t["label"].to_numpy()[hit.clip(0)],
                      [f"m/z {m:.4f}" for m in raw])
    if len(set(labels)) != len(labels):
        raise ValueError(f"{sample} {plane}: non-unique feature labels")
    var.index = pd.Index(labels, dtype=str)
    return var


if __name__ == "__main__":
    src, out = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else DEFAULT_TSV)
    tab = build_table(src)
    tab.to_csv(out, sep="\t", index=False)
    print(f"wrote {out}: {len(tab)} plane-peak annotations")
    print(tab.groupby("sample").agg(planes=("plane", "nunique"), peaks=("mz", "size"),
                                    targeted=("annotation_source", lambda s: s.str.startswith("targeted").sum())))
