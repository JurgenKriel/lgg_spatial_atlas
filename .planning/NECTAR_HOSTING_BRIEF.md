# Hosting the Venture Spatial Atlas on Nectar — Briefing for RCP / HPC

**Prepared for:** WEHI Research Computing Platform (RCP) / HPC team
**Prepared by:** kriel.j (Brain Cancer Research Lab)
**Date:** 2026-07-21 (updated 2026-09-14)
**Status:** **Nectar is now the chosen substrate** (was: fallback). Draft for guidance
and refinement — see the Update block below for what changed and what is already answered.

---

## 0. Update — 2026-09-14

Nectar has been **selected** as the hosting substrate, replacing the interim Cloudflare
R2 decision, primarily on **data-sovereignty and governance** grounds: an Australian,
research-sector, non-commercial cloud avoids the offshore-commercial-cloud question that
gated R2 for unpublished patient-derived data. Cloudflare R2 is retained only as an
optional **post-publication mirror**.

Since this brief was drafted we have verified from Nectar documentation:

- **Trial projects (PT): 4 vCPU, 180 days, and *no* volume or object storage quota.**
  A test site therefore runs on the **30 GB instance root disk** — fine for the 708 MB
  pilot, not for the cohort. A **project allocation is required** for the real thing.
- **Object storage exists** (Swift, plus an S3-compatible API) but is **allocation-gated**
  and **not backed up** — the `/vast` copy stays master.
- **Internet traffic quota: on-net (AARNet) unlimited, off-net 1 GB per core per month.**
  This is now our **largest open question** — see §8.
- Cohort sizing has been derived from the live pilot: **~22 GB / ~45k objects** for
  15 samples × 8 planes (708 MB / 1404 objects measured for 3 planes of one sample),
  so the §6 request of a **100 GB volume** stands, with headroom for two live releases.

A full component inventory, build order and risk register now lives in
`.planning/phases/05-deployment/05-COMPONENTS.md`.

---

## 1. One-paragraph summary

We have built an interactive web atlas of the *Venture* low-grade-glioma spatial
cohort (spatial transcriptomics + aligned MS metabolomics + cell-type + niche
layers). The viewer is a **static web application** (Vitessce, produced by the
haniffalab *webatlas-pipeline*) backed by **chunked Zarr data served over HTTP**.
The data is currently **unpublished** and needs **access-controlled hosting during
peer review**, transitioning to **open public access at publication**. We are
seeking guidance on hosting this on the **Nectar Research Cloud** (a self-managed
VM serving static files), because the WEHI Shiny Server is not a technical fit
(see §3). This document outlines the proposed architecture, resource estimates,
and the specific questions we would like your help with.

---

## 2. What the atlas actually is (technical shape)

Understanding the hosting need depends on two facts:

1. **The viewer is static JavaScript, not an R Shiny app.** Vitessce /
   webatlas-app is a browser single-page application. There is no server-side
   compute at request time — the browser fetches data files directly.
2. **The data is chunked Zarr served over HTTP with CORS.** The viewer issues
   many HTTP range requests for small Zarr chunks (`.zarray` / `.zgroup` metadata
   + binary chunk files). Any host must:
   - serve arbitrary static files (including dotfiles like `.zgroup`),
   - set permissive **CORS headers**,
   - tolerate **many small-object requests** per view.

So the hosting requirement is: **"a static file web server with CORS, holding
tens of GB, reachable by browser, with the ability to gate access during review
and open it later."** It is *not* a compute service.

Current working demo (proof of concept): the pt2 pilot (planes z1–z3) is live on
GitHub Pages at ~708 MB for three planes of one patient. GitHub Pages does not
scale to the full cohort (repo/size limits) and cannot gate access, which is why
we need a proper host.

---

## 3. Why the WEHI Shiny Server does not fit

We reviewed the *Shiny Server Access Policy* (RCP, draft). It is a good fit for R
Shiny apps but not for this workload, for four independent reasons:

| Policy constraint | Our reality | Consequence |
|---|---|---|
| Hosts **R Shiny apps only** | Viewer is a static JS SPA (Vitessce) | Not directly hostable; would need re-implementation |
| **No Milton / `/vast` access** (isolated local storage) | Data lives on HPC filesystems | Data must be *copied* to the host, within quota |
| **1 GB upload limit; ~5 GB auto-approved quota** | 708 MB for **3 planes of one patient**; cohort is tens of GB | Cohort data cannot fit |
| **No authentication supported** | Data is unpublished; needs gated review access | Cannot host unpublished data |

Note the storage and no-Milton limits would sink even a *native R Shiny rewrite*
of the viewer — the cohort-scale Zarr data cannot live on the Shiny server
regardless of framework. **The data must live in dedicated storage we control.**

---

## 4. Proposed solution: two-stage hosting on Nectar

**Stage A — Review (gated, unpublished):**
A single Nectar VM instance running **nginx** serves the Vitessce app **and** the
Zarr data over HTTPS, with **HTTP basic authentication** (or an unguessable
tokenised URL) so anonymous journal reviewers can access it via a URL +
credentials supplied in the cover letter. No login system to build; auth is a few
lines of nginx config.

**Stage B — Publication (open):**
At publication we remove the nginx auth block (open access), and — per the WEHI
policy and journal persistence requirements — deposit the data in a **persistent
archive with a DOI** (e.g. Zenodo/figshare) and, if desired, move the always-on
open host to a maintenance-light managed store (e.g. Cloudflare R2, zero egress
fees) or an institutional static host. The published paper and the repo README
cite the live URL and the DOI.

The key property: **the app and data do not move between stages — we only change
the access control.** Nectar gives us the auth flexibility that WEHI Shiny cannot.

```
                 Stage A (review)                    Stage B (publication)
  Reviewer  ──HTTPS+basic-auth──►  Nectar VM         Anyone ──HTTPS──►  Nectar VM / R2
   (browser)                       (nginx)           (browser)          (open)
                                     │                                     │
                                     ▼                                     ▼
                          static Vitessce app                   + Zenodo DOI (archive)
                          + chunked Zarr (CORS)
```

---

## 5. Architecture on the VM

```
Nectar instance (Ubuntu LTS)
├── nginx
│   ├── serves /var/www/atlas/            → Vitessce SPA (index.html, JS, config)
│   ├── serves /var/www/atlas/data/*.zarr → chunked Zarr (CORS headers set)
│   ├── TLS (Let's Encrypt or institutional cert)
│   └── HTTP basic auth during review (removed at publication)
├── data volume (attached block storage)  → the Zarr stores
└── firewall / security group             → 80/443 in; SSH restricted to WEHI ranges
```

- **Compute is minimal.** Serving static files is I/O- and bandwidth-bound, not
  CPU-bound — unlike a Shiny app, there is no per-request computation. A modest
  instance is sufficient (see §6).
- **Data is refreshed by us**, by copying built Zarr stores from HPC to the VM's
  data volume (rsync/scp over SSH). This is an occasional push, not a live mount.
- **Source & data backup:** app code in git (github.com/JurgenKriel/lgg_spatial_atlas);
  a managed copy of the data retained on Milton, consistent with the WEHI policy's
  backup expectation.

---

## 6. Resource estimate (to refine with you)

| Resource | Estimate | Basis / notes |
|---|---|---|
| **vCPUs** | 2 (up to 4) | Static file serving; low CPU |
| **RAM** | 8 GB | nginx + OS headroom; not compute-bound |
| **Root disk** | 20–30 GB | OS + app |
| **Data volume** | **50–100 GB** | Cohort Zarr **measured at 14 GB** (see below); request headroom for two live releases + rebuilds |
| **Public IP** | 1 | For HTTPS access |
| **Bandwidth** | moderate, bursty | Many small Zarr-chunk requests per viewer session |

**Cohort data size (measured, release `v1-20260923`): 14 GB** — 65 sections
(cells 2.3 GB) plus 39 MS ion-density layers (11.6 GB), ~45k objects. The MS
layers dominate because the niche-metabolomics objects carry every peak-picked
cluster (152–1,238 metabolites per section, 195k–548k pixels), kept in full by
decision 2026-09-23 rather than filtered to confidently annotated peaks. Two
live releases (current + previous, for an atomic swap) therefore need ~30 GB, so
the 50–100 GB request stands and is no longer speculative. Note this is a
**disk** figure, not an egress one: one feature per chunk means a reader pulls
~0.2 MB per metabolite selected, independent of how many peaks a section holds.

---

## 7. Access control & publication lifecycle

- **During review:** nginx **HTTP basic auth** (single shared credential) or a
  tokenised URL. Standard, reviewer-friendly, no login system required. Can
  additionally restrict SSH/admin to WEHI IP ranges via the security group.
- **At publication:** remove auth → open access. Deposit data + config in
  **Zenodo/figshare → mint a DOI**. Cite the DOI and the live URL in the paper and
  the repo README.
- **Persistence:** the git repo + archived DOI become the durable record if the
  VM is ever retired, satisfying the "no dead links in publications" concern the
  WEHI policy raises.

---

## 8. Where we would value your guidance (the asks)

0. **Off-net traffic quota — our most important question.** The published figure is
   **1 GB of off-net traffic per core per month** (on-net/AARNet unlimited). Measured
   on the cohort viewer, a section costs **~3 MB** to open cold and **~0.2 MB** per
   gene or metabolite selected (one feature per Zarr chunk, 2026-09-23), so a
   reviewer working through a z-stack costs tens of MB, not the ~700 MB per three
   planes the pilot's chunking implied. Is this quota **shaped, hard-enforced,
   billed, or advisory** in practice? Is there a path to an exemption or a larger egress
   allowance for a **publication-linked public research atlas**? We will mitigate with
   immutable long-lived cache headers on Zarr chunks (repeat views cost ~nothing), and
   most Australian reviewers are on-net — but overseas reviewers and post-publication
   public traffic are the exposure, and we need an answer before the URL goes into a
   journal cover letter.
1. **Allocation type & duration.** We hold a **trial project** and will stand the test site
   up on it (4 vCPU / 180 days / root-disk only). For the cohort we need a **project
   allocation** with volume + object storage. Can you confirm the right path for WEHI,
   realistic lead time, and whether RCP sponsors or advises on the application?
2. **Storage model.** Block **volume** attached to the VM vs. **object storage (Swift/S3)**
   for ~45k Zarr objects. Which do you recommend, and does the object-storage route change
   the serving/CORS setup (public container + `X-Container-Meta-Access-Control-Allow-Origin`)?
   Can object storage be fronted by the same hostname as the app, so app and data stay
   **same-origin** (which is what lets one basic-auth block cover both)?
3. **Renewal cadence.** How heavy is the annual renewal in practice, and is there an
   institutional path to a longer-term allocation for a publication-linked resource? Our
   concern is a dead link in a published paper.
4. **TLS / DNS.** Preferred approach for HTTPS and the hostname — Let's Encrypt on the
   instance, or an institutional certificate / WEHI-managed subdomain? Is there a WEHI
   position on using an externally-registered domain for this?
5. **Network & security.** Recommended security-group posture; any WEHI policy on
   externally-reachable Nectar instances hosting unpublished data (even basic-auth gated).
6. **Data movement.** Sanctioned path to copy tens of GB from Milton/`/vast` to a Nectar
   volume (we assume `rsync` over SSH, pushed from a SLURM job rather than pulled).
7. **Ops ownership.** We are prepared to own patching/nginx/uptime; is there a baseline
   image, or RCP support, that would reduce that burden?
8. **Alternative you'd prefer.** If RCP has a more suitable managed option for a
   static-file + Zarr workload, we are open to it — hard requirements are in §9.

## 9. Hard requirements (for evaluating any alternative)

Any hosting solution must:

- serve **arbitrary static files including dotfiles**, with **CORS enabled**;
- hold **tens of GB** now, with room to grow to the full cohort;
- support **access control during review** and **open access afterwards**,
  changeable without moving data;
- be reachable by a **standard web browser** at a stable URL (no client-side VM,
  login portal, or special software for viewers).

---

## 10. References

- WEHI *Shiny Server Access Policy* (RCP, draft) — reviewed; see §3.
- webatlas-pipeline (haniffalab): https://github.com/haniffalab/webatlas-pipeline
- Vitessce: http://vitessce.io
- Current pilot (pt2, planes z1–z3): https://jurgenkriel.github.io/lgg_spatial_atlas/
- App source: https://github.com/JurgenKriel/lgg_spatial_atlas

*Numbers marked "estimate" / "to refine" are first-pass and expected to change
after discussion with RCP and once the cohort data builder has run.*
