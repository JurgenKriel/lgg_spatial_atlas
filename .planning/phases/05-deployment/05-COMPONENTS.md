# Phase 5 — Deployment on NECTAR: component plan

**Decision date:** 2026-09-14
**Status:** Substrate locked = **ARDC Nectar Research Cloud**. Supersedes the
2026-07-21 Cloudflare R2 decision in `05-CONTEXT.md` (D-01/D-03/D-04/D-07).
R2 is retained only as the *post-publication* mirror option (see F-4).

---

## 0. What changing to Nectar actually changes

The R2 plan was "managed object store + CDN, no server". Nectar is "a VM we own".
Three consequences fall out of that, and they reshape the phase:

1. **We now own an operating system.** Provisioning, TLS, patching, reboots,
   allocation renewal and disaster recovery become deliverables. Components B and F
   exist entirely because of this and did not exist under R2.

2. **Self-hosting the Vitessce bundle is now a *prerequisite*, not a Milestone-2
   nicety.** The live pilot iframes `https://vitessce.io/?url=<our config>`, i.e. a
   third-party origin fetches our data. The moment we put HTTP basic auth in front
   of the data (the whole point of the review stage), vitessce.io's fetches fail —
   it cannot send our credentials, and a cross-origin credentialed preflight will
   not pass. **Roadmap Phase 7 (self-hosted webatlas-app) must move ahead of, or
   into, Phase 5.** Serving app and data from one origin also removes CORS entirely.

3. **Egress is metered, and this is the sharpest new risk.** Nectar publishes
   **on-net (AARNet) unlimited, off-net 1 GB per core per month**. A 4-core VM =
   ~4 GB/month to the non-AARNet internet. One reviewer opening three z-planes cold
   pulls ~700 MB. That is ~6 external sessions a month before the published quota.
   Australian/AARNet viewers are free; **overseas reviewers and the public are the
   exposure**. See G-1 for mitigations — this needs an answer before the atlas URL
   goes in a cover letter.

---

## 1. Verified Nectar facts (checked 2026-09-14, re-verify at allocation time)

| Fact | Value | Why it matters here |
|---|---|---|
| Trial project (PT) quota | **4 vCPU, 180 days** | Enough for the test site now |
| Trial project storage | **No object storage quota; no volume quota** | Test site must live on the **30 GB instance root disk**. 708 MB pilot fits; the cohort does not. |
| Project allocation | vCPU/SU budget, **volume storage**, **object storage**, instance count, AZ; up to 12 months, renewable | This is what the cohort needs — apply early, it is a merit process |
| Object storage | OpenStack **Swift**, also **S3 API** via EC2 credentials; geo-distributed replicas | Candidate cohort-scale substrate (E-3), and Swift supports public containers + `X-Container-Meta-Access-Control-Allow-Origin` CORS natively |
| Object storage durability | Replicated, but **explicitly not backed up** against deletion | `/vast` stays the master copy (F-2) |
| Internet traffic | **On-net unlimited / off-net 1 GB per core per month** | See G-1 |
| Root disk | 30 GB on standard flavours | Test site ceiling |

Sources are listed at the foot of this document.

---

## 2. Component inventory

Each component: what it is, what artifact it produces, and whether it blocks.

### A. Allocation & governance  *(longest lead time — start these first)*

| # | Component | Artifact | Blocking? |
|---|---|---|---|
| A-1 | **Trial project** (already held) — launch the test site on it | running VM | No — available now |
| A-2 | **Project allocation request** — 12 mo: instances, vCPU/SU, **volume storage 100 GB**, **object storage quota**, AZ (Melbourne), ANZSRC FoR codes, grant linkage, justification incl. an egress note (G-1) | submitted + approved allocation | **Blocks cohort hosting** (not the test site) |
| A-3 | **Research Governance / Risk & Compliance record** — data classification (unpublished, patient-derived), where it rests (AU, ARDC national research cloud), who can reach it, gated-until-publication commitment | a filed record / email approval | **Blocks putting real patient data on the VM.** Much lighter than the R2 case: Nectar is Australian, research-sector, non-commercial — the offshore-commercial-cloud objection that gated R2 disappears |
| A-4 | **WEHI ITS notification + DNS** — an externally reachable host serving institutional data; agree the hostname | ticket ref + DNS record | Soft-blocks the public URL |

### B. Infrastructure (the VM)

| # | Component | Notes |
|---|---|---|
| B-1 | **Instance**: Ubuntu 24.04 LTS, Melbourne AZ, SSH keypair, flavour ~2–4 vCPU / 8 GB | Static serving is I/O-bound, not CPU-bound. Note vCPU count also sets the off-net quota (G-1) |
| B-2 | **Security group**: 80/443 from `0.0.0.0/0`; **22 restricted to WEHI ranges only** | No password SSH |
| B-3 | **Floating IP + DNS name** | TLS needs a *name*. Three options: (a) WEHI subdomain via ITS — best credibility, slowest; (b) own domain (~$15/yr) — fast, survives institutional change, recommended for the public URL; (c) **`sslip.io`/`nip.io` wildcard for the test site today** — zero setup, Let's Encrypt will issue, fine for a throwaway test |
| B-4 | **TLS**: certbot + Let's Encrypt, auto-renew systemd timer | Port 80 must stay reachable for renewal |
| B-5 | **Storage**: test site = root disk. Production = **attached Cinder volume**, ext4, mounted `/srv/atlas/data`, **fstab by UUID** | Volume needs A-2 |
| B-6 | **nginx** — see §3 for the serving rules that are not optional | |
| B-7 | **OS baseline**: `unattended-upgrades`, `ufw`, `fail2ban`, no root login | |

### C. Access control (the review → publication lifecycle)

| # | Component | Notes |
|---|---|---|
| C-1 | **Stage A gate: nginx HTTP basic auth** over app *and* data, one shared reviewer credential | Works cleanly **only because** app and data are same-origin (see §0.2). Keep `htpasswd` out of git |
| C-2 | **OPTIONS/preflight handling** | Only needed if anything stays cross-origin. Same-origin design makes this moot — which is the argument for doing E-1 properly rather than patching CORS |
| C-3 | **Stage B: remove the auth block, same URLs** | App and data do not move between stages — that property is preserved from the R2 plan |
| C-4 | **Zenodo/figshare deposit + DOI** at publication | The durable record if the VM is ever retired; also satisfies journal persistence |
| C-5 | *(optional)* WEHI IP allow-list, or an unguessable token path instead of basic auth | |

### D. Data pipeline & sync (HPC → Nectar)

| # | Component | Notes |
|---|---|---|
| D-1 | **Build staging area on `/vast`** — the existing builders write here unchanged | `/vast` remains the master copy |
| D-2 | **Push sync**: `rsync -e ssh` **from HPC to the VM** (never pull — that would put credentials on the public host). Run from a SLURM job, not the login node | ~45k small files at cohort scale: use `--inplace --whole-file`, or tar-stream and unpack server-side |
| D-3 | **Versioned releases + atomic swap**: upload to `data/v<N>/`, then flip a `current` symlink | Prevents serving a half-synced store. nginx serves through the symlink |
| D-4 | **Post-sync smoke test**: fetch `.zmetadata`, one `.zarray`, one chunk over HTTPS; assert 200 + content-type + byte count | Catches the dotfile trap (§3) immediately |
| D-5 | **Base-URL parameterisation** in `webatlas/build_config_v8.py` | Configs currently hard-code `https://jurgenkriel.github.io/...`. Emit **relative** URLs so one build works on Pages, the test VM and production unchanged |

### E. Application layer

| # | Component | Notes |
|---|---|---|
| E-1 | **Self-hosted Vitessce / webatlas-app** — pin the JS bundle locally, drop the `vitessce.io?url=` iframe | **Prerequisite for gating** (§0.2). Was Roadmap Phase 7 / REQ-12 |
| E-2 | **Landing page** — study description, cohort table, methods, citation, access statement | REQ-18 |
| E-3 | **Swift object storage as the data tier** *(decide after A-2)* | Public container + CORS metadata, VM keeps serving the app. Better for ~45k objects than a VM disk, and takes the data off the instance's failure domain. Fold in only if the allocation grants object quota |

### F. Operations

| # | Component | Notes |
|---|---|---|
| F-1 | **Reproducible provisioning** — cloud-init + a bootstrap script committed to the repo | A Nectar VM is disposable; rebuild must be 20 minutes, not two days. This is the single highest-value ops component |
| F-2 | **Backup/DR** — `/vast` is master; volume snapshot before each release; documented rebuild path | Nectar object storage is *not* backed up |
| F-3 | **Monitoring** — uptime check, disk usage, certbot renewal success, **and off-net egress tracking against the quota** | |
| F-4 | **Allocation renewal calendar entry** (annual) + post-publication mirror decision (R2/Zenodo) | A lapsed allocation = a dead link in a published paper |
| F-5 | **Access-log policy** — retention and what is captured | Logs of a gated patient-data resource; keep it short and documented |

---

## 3. Serving rules that are not optional

These encode failures already paid for once, plus the ones Nectar adds:

- **Serve dotfiles.** Every hardened nginx template ships `location ~ /\. { deny all; }`.
  That 404s `.zarray`, `.zgroup` and `.zmetadata` and the viewer dies silently — the
  exact failure the `.nojekyll` fix cured on Pages. Explicitly allow them.
- **Consolidated metadata is already present** (`.zmetadata` in all 6 stores) — keep it;
  it collapses thousands of metadata round-trips into one per store.
- **Cache-Control: `public, max-age=31536000, immutable` on chunk paths.** Zarr chunks
  are content-immutable under a versioned release path (D-3), so repeat views cost
  ~zero egress. This is a direct G-1 mitigation, not just a nicety.
- **Do not gzip chunk binaries** — already blosc-compressed; gzip wastes CPU and
  disables range requests. Gzip `application/json` (the configs) only.
- **`http2 on`, generous `keepalive_requests`, `open_file_cache`** — the access pattern
  is many small files (median chunk 15 KB, p90 1.5 MB, 1404 objects for the 3-plane pilot).

---

## 4. Build order

### 5a — Test site on the trial allocation  *(no dependencies; do now)*
A-1, B-1…B-4, B-6, B-7, C-1, D-5, E-1(minimal), F-1
**Done when:** the pt2 z1–z3 pilot (708 MB) is served over HTTPS from a Nectar VM,
behind basic auth, with **no vitessce.io dependency**, and a second person opens it
from written instructions. Use synthetic or already-public data if A-3 is not yet
signed off — the point is to prove the stack, not to publish patient data.

### 5b — Allocation & governance  *(run in parallel with 5a)*
A-2, A-3, A-4 — sized by §5 below.

### 5c — Production host
B-5, D-1…D-4, E-2, F-2…F-5, and E-3 if object quota was granted.
**Done when:** the full pt2 atlas (all 8 planes) is served from the volume, a release
can be re-synced atomically, and the VM can be rebuilt from committed config.

### 5d — Publication
C-3, C-4, F-4.

Phase 6 (cohort manifest/selector) and Phase 8 (image + segmentation layers) are
unblocked once 5c lands. Roadmap Phase 10 reduces to the 5d tasks.

---

## 5. Sizing (derived from the live pilot, not guessed)

Pilot measured: **708 MB / 1404 objects** for 3 z-planes of one sample (cells + MS),
i.e. **~236 MB / ~470 objects per plane-pair**.

| Tranche | Planes | Est. size | Est. objects |
|---|---|---|---|
| 6 ST+SM samples (ven1–ven6) × 8 planes | 48 | ~11 GB | ~22k |
| 9 ST-only samples × 8 planes (cells only) | 72 | ~11 GB | ~22k |
| **Cohort total** | 120 | **~22 GB** | **~45k** |

Consistent with the 20–40 GB in `NECTAR_HOSTING_BRIEF.md` §6. **Request 100 GB** —
headroom for two live releases plus rebuilds. Note Phase 8 (pyramidal H&E/IF OME-Zarr)
is what will actually consume that headroom, at GB-per-plane scale; re-size before
Phase 8 rather than assuming 100 GB covers it.

---

## 6. Risks

| # | Risk | Mitigation |
|---|---|---|
| **G-1** | **Off-net egress quota (1 GB/core/month)** throttles or bills external reviewers | (a) Ask Nectar support whether it is shaped, enforced or advisory — do this before quoting a URL in a cover letter; (b) immutable long-lived cache headers (§3) so repeat views are free; (c) AARNet viewers are unmetered — most Australian reviewers cost nothing; (d) request more cores (quota scales per core) and justify egress in A-2; (e) at publication, mirror to R2/Zenodo where egress is free — the original R2 argument survives as the *post*-publication answer |
| **G-2** | Trial project has no volume/object quota → test site capped at the 30 GB root disk | Eased: the cohort release measures **14 GB** (2026-09-23), so it fits the root disk for testing, with no room for a second release or snapshots; production still waits on A-2 |
| **G-3** | Basic auth breaks the vitessce.io iframe | E-1 — self-host the bundle, same origin (§0.2) |
| **G-4** | VM/allocation loss = data loss and a dead published link | `/vast` master copy (F-2), committed provisioning (F-1), renewal reminder (F-4), DOI deposit (C-4) |
| **G-5** | Nginx dotfile default 404s Zarr metadata | §3 + the D-4 smoke test |
| **G-6** | ~45k small objects on a single VM disk | E-3 (Swift) if object quota lands; otherwise acceptable — measured chunk sizes are moderate, not pathological |

---

## 7. Immediate next actions

1. Launch the trial-project VM and stand up 5a — this needs nothing from anyone else.
2. Email Nectar support the G-1 question (off-net enforcement for a public research atlas).
3. Start A-3 (governance) and A-2 (allocation) in parallel; both have external lead time.
4. Land D-5 (relative URLs) in the build — it is a small change that unblocks hosting anywhere.

---

## Sources

- Nectar trial quotas / resources: https://support.ehelp.edu.au/support/solutions/articles/6000055380-resources-available-to-you
- Trial projects & allocations: https://tutorials.rc.nectar.org.au/allocation-management/03-account-and-trial
- Object storage overview: https://tutorials.rc.nectar.org.au/object-storage/01-overview
- Swift CORS: https://docs.openstack.org/swift/latest/cors.html
- Volume storage allocation: https://tutorials.rc.nectar.org.au/volume-storage/02-allocation
- Prior briefs: `.planning/NECTAR_HOSTING_BRIEF.md`, `.planning/OBJECT_STORAGE_HOSTING_BRIEF.md`

*Phase: 05-deployment — component plan, 2026-09-14*
