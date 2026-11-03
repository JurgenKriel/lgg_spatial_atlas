# Phase 5: Deployment & sharing - Context

> **SUPERSEDED IN PART (2026-09-14): the hosting substrate is now the ARDC Nectar
> Research Cloud, not Cloudflare R2.** Decisions **D-01, D-03, D-04, D-07** below are
> historical — read `05-COMPONENTS.md` for the current component plan. What still
> stands: **D-02** (Shiny rejected), **D-05/D-06** (gated review -> open + DOI, app and
> data don't move between stages), and **D-08**'s governance requirement, which Nectar
> makes materially easier to satisfy (Australian, research-sector, non-commercial).
> R2 survives only as the optional *post-publication* mirror.

**Gathered:** 2026-07-21
**Status:** Superseded in part — substrate re-decided to Nectar 2026-09-14

<domain>
## Phase Boundary

Collaborators can open the pt2 atlas with documented steps, on a hosting substrate
that carries the unpublished→published lifecycle. Cohort-scale generalization is
Phase 6; production frontend/image layers are Milestone 2 (Phases 7–10). This phase
locks the *hosting substrate and access lifecycle* those later phases inherit.

</domain>

<decisions>
## Implementation Decisions

### Hosting substrate — Cloudflare R2 + Cloudflare CDN (chosen 2026-07-21)
- **D-01:** Host the **static Vitessce app + chunked Zarr on Cloudflare R2**,
  fronted by **Cloudflare** (custom domain, automatic TLS, global CDN edge
  caching, CORS). Fully managed — **no VM to run, patch, or rebuild**. Grant funds
  cover the (small) cost. Chosen over the self-managed Nectar VM for lower ops
  burden, managed durability, and no allocation-renewal cycle.
- **D-02:** WEHI Shiny Server remains **rejected** (see `NECTAR_HOSTING_BRIEF.md`
  §3): Shiny-only, no Milton/`/vast` access, 1 GB upload / ~5 GB quota vs.
  tens-of-GB data, no auth. Framework-independent conclusion: **the Zarr data must
  live in dedicated storage we control** — R2 satisfies this.
- **D-03:** Data is pushed to the R2 bucket from HPC via the **S3 API**
  (`rclone` / `aws s3 sync`) as an occasional refresh — not a live mount.
- **D-04:** S3 (+ CloudFront) is the **documented fallback** if an AWS account is
  mandated; R2 is preferred because its **zero egress** removes the dominant,
  least-predictable cost for a chunk-heavy viewer.

### Access lifecycle — gated review → open at publication (two stage)
- **D-05:** **Stage A (under review):** a small **Cloudflare Worker enforces HTTP
  basic auth** on every request (app + all Zarr chunks) — one shared credential,
  given to reviewers in the cover letter. (Cloudflare Access with email OTP is an
  alternative if per-reviewer control is ever wanted; CloudFront signed cookies is
  the AWS equivalent.)
- **D-06:** **Stage B (at publication):** remove the Worker → open access. Deposit
  data + config in **Zenodo/figshare** and **mint a DOI**; cite the DOI + live URL
  in the paper and repo README. **App and data do not move between stages — only
  the Worker/auth changes.** No separate landing page (WEHI Shiny included).

### Cost envelope (funds available)
- **D-07:** ~**$2–8/month** on R2 for the full cohort (~20–40 GB): storage
  $0.015/GB-mo, reads $0.36/M ops, **egress free**, Worker ~$0–5/mo. Comfortably
  within grant funds; no capacity planning or allocation renewal.

### Data governance — the gating precondition
- **D-08:** R2 hosting of **unpublished, patient-derived** data is **conditional on
  Research Governance / Risk & Compliance sign-off** (commercial, possibly offshore
  cloud). Mitigations: **pin storage to an Australian region / R2 jurisdiction
  hint**, keep the data **access-controlled (D-05) until publication**. If
  governance disallows commercial-cloud storage of unpublished data, the **Nectar
  VM** (`NECTAR_HOSTING_BRIEF.md`) is the fallback for the review stage, migrating
  to R2 at publication when the data is public anyway.

### Claude's Discretion
- Cloudflare Worker basic-auth implementation, CORS rules, custom-domain wiring,
  and R2 bucket layout — planning-time detail.
- Whether to use Cloudflare Access vs. a Worker for review gating.

</decisions>

<specifics>
## Specific Ideas

- Data is **currently unpublished**, intended to become **publicly available after
  publication** — this drove the gated→open two-stage requirement.
- Reference targets remain gbmspace.org / cellatlas.io (object-store-backed
  Vitessce), directly consistent with the R2 substrate.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Hosting decision & requirements
- `.planning/OBJECT_STORAGE_HOSTING_BRIEF.md` — **chosen option**: R2 architecture
  (§2), why-easier-than-Nectar (§3), review gating via Worker (§4), cost (§5),
  governance caveat (§6), and RCP/Governance questions (§8).
- `.planning/NECTAR_HOSTING_BRIEF.md` — the self-managed-VM **fallback** if
  governance blocks commercial-cloud storage; also the source for why-not-Shiny
  (§3) and the hard host requirements (§9).
- `scripts/ShinyServerManagementPolicy.pdf` (BCRL parent repo) — the WEHI policy
  ruling out Shiny hosting.

### Prior state
- `.planning/HANDOFF.md` — current live pilot (pt2 z1–z3 on GitHub Pages, 708 MB),
  build pipeline, and hosting-ceiling notes.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Existing Vitessce build (`webatlas/build_config_v8.py`, `build/*`) is unchanged —
  R2 serves the same static output; only the host moves off GitHub Pages.
- `.nojekyll` / dotfile-serving lessons carry over: R2 + CORS must serve Zarr
  dotfiles (`.zgroup`/`.zarray`).

### Integration Points
- Data-refresh path: HPC-built Zarr → `rclone`/`aws s3 sync` → R2 bucket → CDN.

</code_context>

<deferred>
## Deferred Ideas — reconciled into Milestone 2

The R2 decision **absorbs** Milestone 2's separate hosting phases:
- **Phase 7 (self-hosted webatlas-app frontend)** — served from R2 + Cloudflare
  alongside the Vitessce assets; no separate hosting substrate to provision.
- **Phase 10 (object-storage hosting)** — this **is** the Phase 5 substrate now;
  Phase 10 reduces to publication-stage tasks (open the bucket, Zenodo DOI, final
  cohort sizing), not a separate migration.
- Cohort-scale data volume (Phase 6) informs storage cost but does not change the
  substrate decision.

</deferred>

---

*Phase: 05-deployment*
*Context gathered: 2026-07-21*
