# Hosting the Venture Spatial Atlas on Object Storage (Cloudflare R2 / S3) — Justification

**Prepared for:** WEHI Research Computing Platform (RCP) / HPC team
**Prepared by:** kriel.j (Brain Cancer Research Lab)
**Date:** 2026-07-21
**Status:** Draft for guidance and refinement
**Companion doc:** `NECTAR_HOSTING_BRIEF.md` (the self-managed-VM alternative)

---

## 1. One-paragraph summary

We propose hosting the *Venture* spatial atlas — a **static Vitessce web app backed
by chunked Zarr data** (see `NECTAR_HOSTING_BRIEF.md` §2 for the technical shape) —
directly from **cloud object storage fronted by a CDN**, specifically
**Cloudflare R2 + Cloudflare** (with Amazon S3 + CloudFront as the equivalent
alternative). This is a **fully managed, near-zero-ops** solution: there is no
virtual machine to provision, patch, keep running, or rebuild, and no allocation
to renew. Given that we have **funds to cover the (small) hosting cost**, this is
the simpler and more durable option compared with a self-managed Nectar VM. The
one workflow requirement that object storage does not provide out-of-the-box —
**access control during peer review** — is fully solved with a small Cloudflare
Worker (basic auth), so the gated-review→open-at-publication lifecycle is preserved.

---

## 2. Proposed architecture

```
                         Cloudflare (DNS + CDN + TLS)
                                   │
                 ┌─────────────────┴───────────────────┐
   Reviewer /    │  Cloudflare Worker (review stage):   │
   collaborator ─►  HTTP basic auth on every request    │   ← removed at publication
   (browser)      └─────────────────┬───────────────────┘
                                     ▼
                        Cloudflare R2 bucket
                        ├── /atlas/            → Vitessce SPA (index.html, JS, config)
                        └── /atlas/data/*.zarr → chunked Zarr (CORS enabled)
```

- **R2 bucket** holds both the static app and the Zarr data. R2 serves static
  files (including Zarr dotfiles `.zgroup`/`.zarray`) with configurable **CORS**,
  which is all the viewer needs.
- **Custom domain via Cloudflare** (e.g. `atlas.<domain>`), with automatic TLS and
  global CDN caching — chunk reads are edge-cached, so external collaborators get
  fast loads without us running any server.
- **No compute instance.** Data is uploaded from HPC with the S3-compatible CLI
  (`rclone`/`aws s3`/`wrangler`) — an occasional push, same as any object store.
- **S3 + CloudFront** is the functional equivalent if an AWS account is preferred
  (see §5 for why R2 is the cheaper default for this workload).

---

## 3. Why this is easier than a Nectar VM (the core justification)

| Dimension | Nectar VM (self-managed) | Object storage (R2/S3) |
|---|---|---|
| **Server to manage** | Yes — OS, nginx, patching, uptime, rebuild-on-failure is the owner's responsibility | **None** — fully managed service |
| **Allocation lifecycle** | Project allocation ~12 mo, **renewable** (recurring admin); trial only ~3 mo | **No renewal** — pay-as-you-go, persists indefinitely |
| **Durability / backup** | Volume **not backed up** (per Nectar); we must back up ourselves | **11 nines** managed durability; replicated by the provider |
| **Scaling** | Must size the volume up front and resize later | **Elastic** — no capacity planning, no size guess |
| **Performance for external users** | Single VM, single region, our bandwidth | **Global CDN** edge caching included |
| **Cost model** | "Free" allocation but our ops time + renewals | Small, predictable $ (we have funds) — **buys away the ops burden** |
| **Ops skill required** | Linux sysadmin (nginx, TLS, firewall) | Bucket config + a few lines of Worker code |

The trade we are making is explicit and deliberate: **spend a small amount of grant
money to remove server administration, allocation renewals, and backup
responsibility entirely.** For a lab whose time is better spent on the science,
that is the right trade.

---

## 4. Access lifecycle — gated review → open (the one gap, solved)

Object storage is public-or-private at the bucket level and has no built-in login,
which is why this needs a deliberate design. It is fully solvable:

- **Stage A — under review (gated):** put a **Cloudflare Worker** in front of the
  bucket that enforces **HTTP basic auth** (a few lines; one shared credential).
  This covers *every* request — app and all Zarr chunks — so anonymous journal
  reviewers get a URL + credentials in the cover letter, exactly as with the
  nginx approach. (Cloudflare **Access** with a one-time email PIN is an
  alternative if per-reviewer control is ever wanted.)
- **Stage B — at publication (open):** remove the Worker (or set it to
  pass-through) → open access. Deposit data + config in **Zenodo/figshare → mint a
  DOI**; cite the DOI and live URL in the paper and repo README. **App and data do
  not move — only the Worker/auth changes.**

> On AWS the equivalent is **CloudFront signed cookies** (one login sets a cookie
> that authorises all paths under the distribution) — also whole-site, also
> removable at publication.

This preserves the exact lifecycle that motivated the hosting decision, with no VM.

---

## 5. Cost estimate (funds available)

Cohort Zarr is estimated at **~20–40 GB** (see `NECTAR_HOSTING_BRIEF.md` §6). For a
spatial viewer, **reads (GET) dominate** — a browsing session issues thousands of
small chunk requests.

**Cloudflare R2 (recommended):**
| Item | Rate | ~Monthly at our scale |
|---|---|---|
| Storage | $0.015 / GB-mo | ~40 GB → **~$0.60** |
| Class B ops (reads) | $0.36 / million | moderate traffic → **~$1–3** |
| Class A ops (writes/uploads) | $4.50 / million | occasional pushes → **~$0** |
| **Egress / bandwidth** | **$0 (free)** | **$0** |
| Worker (auth, review stage) | $5/mo plan or free tier | ~$0–5 |
| **Total** | | **~$2–8 / month** |

**Why R2 over S3 for this workload:** S3 charges **egress (~$0.09/GB)**, and a
chunk-heavy viewer under external traffic makes egress the dominant, least
predictable cost. R2's **zero egress** removes that variable entirely. S3 +
CloudFront narrows the gap (CloudFront caches, egress ~$0.085/GB) but adds
configuration. **R2 is the cheaper, simpler default; S3+CloudFront is the fallback
if an AWS account is mandated.**

Either way the cost is **a few dollars a month** — comfortably within available
funds, and it buys away all the ops burden in §3.

---

## 6. The one thing to verify — data governance

This is the material caveat and the main reason to loop in RCP / Research
Governance before committing:

- The atlas data is **unpublished, patient-derived** spatial data. Storing it on a
  **commercial, potentially offshore cloud** (Cloudflare/AWS) may engage WEHI data-
  governance, ethics, and data-residency requirements — even during the gated
  review stage, and even though it is processed/de-identified spatial data.
- **Mitigations:** pin storage to an **Australian region** where required
  (AWS `ap-southeast-2` Sydney; R2 supports jurisdictional **location hints** to
  constrain data placement), keep the data **access-controlled until publication**
  (§4), and confirm the arrangement with **Research Governance, Risk & Compliance**.
- If governance disallows commercial-cloud storage of unpublished patient data,
  the **Nectar VM option** (institutional/AU research cloud) is the fallback for
  the review stage, with a possible **move to R2/S3 at publication** when the data
  is public anyway.

Everything else (compliance with licences/agreements) mirrors the Nectar brief.

---

## 7. Recommendation

**Host on Cloudflare R2 + Cloudflare**, with a Worker enforcing basic auth during
review and removed at publication, plus a Zenodo DOI at publication.

- **If** Research Governance approves commercial-cloud storage of the unpublished
  data (region-pinned, access-controlled) → R2 is the simpler, more durable,
  lower-ops choice and is the recommended path.
- **If** governance requires institutional infrastructure for unpublished data →
  use Nectar for the review stage (`NECTAR_HOSTING_BRIEF.md`) and optionally
  migrate to R2/S3 at publication.

The two docs are deliberately parallel so RCP can advise on the governance question
and we can pick the substrate without any other part of the plan changing.

---

## 8. Questions for RCP / Governance

1. **Governance:** May unpublished patient-derived spatial data be stored on
   commercial cloud object storage (Cloudflare R2 / AWS S3) during peer review,
   given region-pinning and access control? If not, is publication-stage (open)
   commercial hosting acceptable?
2. **Region / residency:** Any WEHI requirement for Australian data residency that
   dictates AWS `ap-southeast-2` over Cloudflare's global placement (or R2
   jurisdiction hints)?
3. **Account & billing:** Does WEHI have an institutional AWS/Cloudflare account
   and billing path we should use, or do we set up a lab-owned account against our
   grant funds?
4. **Preferred vendor:** Any institutional preference or existing agreement
   (AWS vs Cloudflare) that should decide R2 vs S3+CloudFront?
5. **Data movement:** Sanctioned path to push tens of GB from Milton/`/vast` to the
   bucket (`rclone`/`aws s3 sync` over the S3 API is our assumption).

---

## 9. Hard requirements (unchanged — for evaluating any host)

Any hosting solution must serve **arbitrary static files including dotfiles with
CORS**, hold **tens of GB** with room to grow, support **access control during
review → open afterwards without moving data**, and be reachable by a **standard
browser** at a stable URL. See `NECTAR_HOSTING_BRIEF.md` §9.

---

## 10. References

- Companion: `.planning/NECTAR_HOSTING_BRIEF.md` — self-managed Nectar VM option.
- Cloudflare R2: https://developers.cloudflare.com/r2/  (pricing, custom domains, CORS)
- Cloudflare Workers / Access: https://developers.cloudflare.com/workers/  ·  https://developers.cloudflare.com/cloudflare-one/
- Amazon S3 + CloudFront (signed cookies): https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-signed-cookies.html
- webatlas-pipeline / Vitessce (data format): see `NECTAR_HOSTING_BRIEF.md` §10.

*Numbers marked "estimate" are first-pass and expected to change after discussion
with RCP and once the cohort data builder has run.*
