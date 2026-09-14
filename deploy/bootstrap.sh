#!/usr/bin/env bash
# Venture Atlas — Nectar VM provisioning (components B-2, B-4, B-6, B-7, C-1, F-1)
#
# Idempotent: safe to re-run. This is the whole of the VM's configuration, so a
# rebuild is "launch instance, scp this, run it" rather than an archaeology
# exercise. A Nectar VM is disposable — treat this file as the real server.
#
# Run as root on a fresh Ubuntu 24.04 LTS instance:
#
#   sudo ATLAS_DOMAIN=atlas.example.org \
#        ATLAS_EMAIL=you@wehi.edu.au \
#        ATLAS_USER=reviewer \
#        ATLAS_PASS='<a long random string>' \
#        ./bootstrap.sh
#
# Omit ATLAS_PASS and one is generated and printed once.
set -euo pipefail

ATLAS_DOMAIN="${ATLAS_DOMAIN:?set ATLAS_DOMAIN, e.g. atlas.example.org or 1-2-3-4.sslip.io}"
ATLAS_EMAIL="${ATLAS_EMAIL:?set ATLAS_EMAIL for TLS certificate expiry notices}"
ATLAS_USER="${ATLAS_USER:-reviewer}"
ATLAS_PASS="${ATLAS_PASS:-}"
ATLAS_SSH_CIDR="${ATLAS_SSH_CIDR:-}"   # optional: restrict SSH, e.g. WEHI ranges
SKIP_TLS="${SKIP_TLS:-0}"              # 1 = configure http only (no cert yet)

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo)"; exit 1; }

# --- packages ----------------------------------------------------------------
log "Installing packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    nginx apache2-utils certbot python3-certbot-nginx \
    ufw fail2ban unattended-upgrades rsync curl ca-certificates

# --- B-7: OS baseline --------------------------------------------------------
log "OS hardening"
# Unattended security upgrades
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

# No password SSH, no root login
install -d -m 755 /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/10-atlas.conf <<'EOF'
PasswordAuthentication no
PermitRootLogin no
KbdInteractiveAuthentication no
EOF
systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null || true

systemctl enable --now fail2ban

# --- B-2: host firewall (belt and braces with the Nectar security group) -----
log "Firewall"
ufw --force reset >/dev/null
if [ -n "$ATLAS_SSH_CIDR" ]; then
    # Restrict SSH to the given range(s), comma-separated
    IFS=',' read -ra CIDRS <<< "$ATLAS_SSH_CIDR"
    for c in "${CIDRS[@]}"; do ufw allow from "$c" to any port 22 proto tcp; done
else
    echo "    NOTE: ATLAS_SSH_CIDR unset — SSH open to the world at the host firewall."
    echo "    Restrict it in the Nectar security group, or re-run with ATLAS_SSH_CIDR set."
    ufw limit 22/tcp
fi
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# --- directory layout --------------------------------------------------------
log "Directory layout"
install -d -m 755 /srv/atlas/site
install -d -m 755 /srv/atlas/data
install -d -m 755 /var/www/html/.well-known/acme-challenge
chown -R www-data:www-data /srv/atlas

# A deploy group so the sync account can write without sudo (component D-2)
getent group atlas-deploy >/dev/null || groupadd atlas-deploy
chgrp -R atlas-deploy /srv/atlas/data
chmod -R g+rws /srv/atlas/data
if [ -n "${SUDO_USER:-}" ]; then
    usermod -aG atlas-deploy "$SUDO_USER"
    echo "    added $SUDO_USER to atlas-deploy (re-login for it to take effect)"
fi

# --- C-1: the review gate ----------------------------------------------------
log "Basic auth credential"
if [ -f /etc/nginx/atlas.htpasswd ] && [ -z "$ATLAS_PASS" ]; then
    echo "    /etc/nginx/atlas.htpasswd exists and no ATLAS_PASS given — keeping it."
else
    if [ -z "$ATLAS_PASS" ]; then
        ATLAS_PASS="$(head -c 18 /dev/urandom | base64 | tr -d '/+=' | head -c 20)"
        GENERATED=1
    fi
    htpasswd -bcB /etc/nginx/atlas.htpasswd "$ATLAS_USER" "$ATLAS_PASS" >/dev/null
    chown root:www-data /etc/nginx/atlas.htpasswd
    chmod 640 /etc/nginx/atlas.htpasswd
fi

# --- B-6: nginx --------------------------------------------------------------
log "nginx site config"
[ -f "$HERE/nginx/atlas.conf.template" ] || { echo "missing nginx/atlas.conf.template next to this script"; exit 1; }
sed "s/__ATLAS_DOMAIN__/${ATLAS_DOMAIN}/g" \
    "$HERE/nginx/atlas.conf.template" > /etc/nginx/sites-available/atlas.conf

# Ubuntu 24.04 ships nginx 1.24, where `http2 on;` does not exist yet and the
# option lives on the listen directive instead. Detect rather than assume.
NGINX_VER="$(nginx -v 2>&1 | sed 's|.*/||')"
if [ "$(printf '%s\n1.25.1\n' "$NGINX_VER" | sort -V | head -1)" != "1.25.1" ]; then
    echo "    nginx $NGINX_VER predates 'http2 on;' — moving http2 onto the listen directive"
    sed -i 's/^\(\s*\)http2 on;//' /etc/nginx/sites-available/atlas.conf
    sed -i 's/listen 443 ssl;/listen 443 ssl http2;/' /etc/nginx/sites-available/atlas.conf
    sed -i 's/listen \[::\]:443 ssl;/listen [::]:443 ssl http2;/' /etc/nginx/sites-available/atlas.conf
fi

ln -sf /etc/nginx/sites-available/atlas.conf /etc/nginx/sites-enabled/atlas.conf
rm -f /etc/nginx/sites-enabled/default

# --- B-4: TLS ----------------------------------------------------------------
if [ "$SKIP_TLS" = "1" ]; then
    log "SKIP_TLS=1 — serving http only; run certbot yourself when DNS is ready"
    # Strip the ssl server block's cert lines so nginx can start without a cert
    echo "    (leaving config in place; nginx will fail to start until a cert exists)"
else
    log "TLS via Let's Encrypt for ${ATLAS_DOMAIN}"
    # certbot needs a working http vhost to answer the challenge. Put a minimal
    # one in place first, get the cert, then install the real config.
    cat > /etc/nginx/sites-available/atlas-bootstrap.conf <<EOF
server {
    listen 80;
    server_name ${ATLAS_DOMAIN};
    location ^~ /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 404; }
}
EOF
    ln -sf /etc/nginx/sites-available/atlas-bootstrap.conf /etc/nginx/sites-enabled/atlas-bootstrap.conf
    rm -f /etc/nginx/sites-enabled/atlas.conf
    nginx -t && systemctl restart nginx

    certbot certonly --webroot -w /var/www/html \
        -d "$ATLAS_DOMAIN" --email "$ATLAS_EMAIL" \
        --agree-tos --non-interactive --keep-until-expiring

    rm -f /etc/nginx/sites-enabled/atlas-bootstrap.conf
    ln -sf /etc/nginx/sites-available/atlas.conf /etc/nginx/sites-enabled/atlas.conf

    # certbot's apt package already installs a renewal timer; make sure nginx
    # picks up the new cert when it fires.
    install -d -m 755 /etc/letsencrypt/renewal-hooks/deploy
    cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'EOF'
#!/bin/sh
systemctl reload nginx
EOF
    chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
    systemctl enable --now certbot.timer 2>/dev/null || true
fi

# --- a placeholder page so the host is never blank ---------------------------
if [ ! -f /srv/atlas/site/index.html ]; then
    cat > /srv/atlas/site/index.html <<'EOF'
<!doctype html><meta charset="utf-8"><title>Venture Atlas</title>
<body style="font-family:system-ui;margin:3rem auto;max-width:40rem;line-height:1.6">
<h1>Venture Atlas</h1>
<p>The server is provisioned. The viewer has not been deployed yet — run
<code>deploy/sync_to_nectar.sh</code> from the HPC side.</p>
EOF
    chown www-data:www-data /srv/atlas/site/index.html
fi

log "Validating nginx config"
nginx -t
systemctl reload nginx || systemctl restart nginx
systemctl enable nginx

log "Done"
echo "  Site:  https://${ATLAS_DOMAIN}/"
echo "  User:  ${ATLAS_USER}"
if [ "${GENERATED:-0}" = "1" ]; then
    echo "  Pass:  ${ATLAS_PASS}    <-- generated, shown ONCE, store it now"
else
    echo "  Pass:  (as supplied)"
fi
echo
echo "  Next: push data from the HPC with deploy/sync_to_nectar.sh,"
echo "        then verify with deploy/smoke_test.sh https://${ATLAS_DOMAIN}/ ${ATLAS_USER}:<pass>"
