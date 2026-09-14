# Phase 5a — test site on the Nectar trial allocation

A runbook. Everything here targets the **trial project** you already hold, which
is enough to prove the whole serving stack. Nothing in 5a needs the project
allocation, governance sign-off, or anyone else's calendar.

> **Trial constraint that shapes this stage:** a Nectar trial project gets
> **4 vCPU, 180 days, and no volume or object storage quota**. The site therefore
> lives on the instance's **30 GB root disk**. The 708 MB pt2 pilot fits
> comfortably; the ~22 GB cohort does not, and waits on the allocation (5b).

> **Data caution:** until Research Governance has signed off (component A-3),
> treat this as a stack test. Use the pilot only if you are content for it to sit
> behind basic auth on a Nectar VM; otherwise point `--src` at synthetic data.
> The point of 5a is to prove the serving path, not to publish patient data.

---

## What you do on the Nectar dashboard

1. **Launch an instance** — Ubuntu 24.04 LTS, Melbourne AZ, flavour with 2–4
   vCPU. Add your SSH key.
   *Note the vCPU count also sets the off-net egress allowance (1 GB per core
   per month), so 4 vCPU buys 4 GB/month to the non-AARNet internet.*
2. **Security group** — allow `80/tcp` and `443/tcp` from anywhere; restrict
   `22/tcp` to WEHI ranges.
3. **Allocate and attach a floating IP.**
4. **Give it a name.** TLS needs a hostname, not an IP. Fastest option that works
   today with no registrar and no ITS ticket:
   `<dashed-ip>.sslip.io` — e.g. floating IP `203.0.113.7` → `203-0-113-7.sslip.io`.
   Let's Encrypt issues for it. Swap in a real domain later; nothing else changes.

## What you run

```bash
# 1. from your laptop / an HPC login node — ship the provisioning files
scp -r deploy ubuntu@<floating-ip>:~/

# 2. on the VM — one command provisions the whole host
ssh ubuntu@<floating-ip>
sudo ATLAS_DOMAIN=203-0-113-7.sslip.io \
     ATLAS_EMAIL=you@wehi.edu.au \
     ATLAS_USER=reviewer \
     ATLAS_SSH_CIDR=<wehi-range>/24 \
     ./deploy/bootstrap.sh
# prints the generated reviewer password ONCE — store it now
```

`bootstrap.sh` installs nginx, certbot, ufw, fail2ban and unattended-upgrades,
lays out `/srv/atlas`, writes the htpasswd, installs the site config, obtains the
TLS certificate and sets up renewal. It is idempotent — re-run it freely.

```bash
# 3. from the HPC — build the viewer bundle, then push app + data
./app/build.sh --install                       # first time only, ~10 min
rsync -a app/index.html app/vendor ubuntu@<ip>:/srv/atlas/site/

sbatch --job-name=atlas-sync --cpus-per-task=4 --mem=8G --time=2:00:00 \
  --wrap "deploy/sync_to_nectar.sh --host ubuntu@<floating-ip> --version v1"

# 4. verify — this is the step that catches the silent failures
./deploy/smoke_test.sh https://203-0-113-7.sslip.io/ reviewer:<password>
```

---

## What each piece is

| File | Component | What it does |
|---|---|---|
| `bootstrap.sh` | B-2, B-4, B-6, B-7, C-1, F-1 | The entire server config, idempotent. A Nectar VM is disposable — this file *is* the server, so a rebuild is twenty minutes. |
| `nginx/atlas.conf.template` | B-6, C-1 | The serving rules. Read the header comment before editing. |
| `sync_to_nectar.sh` | D-2, D-3 | Pushes a versioned release from HPC and flips `current` atomically. Generates the manifest. |
| `smoke_test.sh` | D-4 | Verifies the rules that fail silently in a browser. |
| `../app/` | E-1, D-5 | The self-hosted viewer that replaces the vitessce.io iframe. |

## Layout on the server

```
/srv/atlas/site/           the app — index.html, vendor/
/srv/atlas/data/v1/        a release: zarr stores, configs, manifest.json  (IMMUTABLE)
/srv/atlas/data/v2/        the next release
/srv/atlas/data/current -> v2                                    (the only mutable path)
/etc/nginx/atlas.htpasswd  the review credential — never in git
```

Releases are immutable and the symlink flip is atomic, so a half-finished rsync
is never servable and a rollback is one `ln -sfn` away.

## The four things that break this deploy

All four are silent in a browser; `smoke_test.sh` checks every one.

1. **A dotfile deny rule.** The stock nginx hardening snippet
   `location ~ /\. { deny all; }` 404s `.zarray`, `.zgroup` and `.zmetadata`,
   and the viewer renders a blank panel. It also breaks certbot renewal. This is
   the same failure `.nojekyll` cured on GitHub Pages.
2. **A third-party viewer.** If the page loads Vitessce from vitessce.io or a
   CDN, the review gate leaks or the data fails to load — that origin cannot
   send your credentials. Hence the vendored bundle in `app/vendor/`.
3. **Auth over the ACME challenge path.** Certificate renewal fails silently
   ~60 days later, and the site goes dark at day 90.
4. **Gzipping chunk binaries.** They are already blosc-compressed; gzip wastes
   CPU and disables range requests. Only JSON is compressed.

## Opening it up at publication (Stage B, phase 5d)

Comment out the two `auth_basic` lines in
`/etc/nginx/sites-available/atlas.conf` and `systemctl reload nginx`. Nothing
moves, no URL changes, no rebuild. Then deposit for a DOI (component C-4).

## Egress — watch this

The published quota is **1 GB of off-net traffic per core per month**; on-net via
AARNet is unlimited. One cold three-plane session pulls roughly 700 MB, so a
4 vCPU instance covers about five and a half overseas sessions a month. The
immutable cache headers make repeat views nearly free, and Australian reviewers
cost nothing. Before quoting this URL in a cover letter, ask Nectar support
whether the quota is shaped, enforced, billed or advisory (risk G-1).

Check what you have actually served:

```bash
# rough off-net bytes this month, from the nginx access log
awk '{s+=$10} END {printf "%.2f GB\n", s/1024/1024/1024}' /var/log/nginx/atlas.access.log
```

---

*Phase 5a of `.planning/phases/05-deployment/05-COMPONENTS.md`.*
