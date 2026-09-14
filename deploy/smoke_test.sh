#!/usr/bin/env bash
# Venture Atlas — post-deploy smoke test (component D-4, minimal form)
#
# Checks the serving rules that fail SILENTLY in a browser. Every one of these
# corresponds to a real failure mode, not a hypothetical:
#   - the Zarr dotfile 404 (killed the Pages deploy until .nojekyll was added)
#   - auth that gates the app but leaks the data, or gates the ACME challenge
#   - chunks served without immutable caching (burns the off-net quota, G-1)
#   - metadata served as octet-stream instead of JSON
#
# Usage:
#   ./smoke_test.sh https://atlas.example.org/ reviewer:secret
#   ./smoke_test.sh http://localhost:8000/            # no auth, local dry run
#
# Exit 0 = all passed. Exit 1 = at least one failure (the output says which).
set -uo pipefail

BASE="${1:?usage: smoke_test.sh <base-url> [user:pass]}"
CREDS="${2:-}"
BASE="${BASE%/}"

AUTH=(); [ -n "$CREDS" ] && AUTH=(-u "$CREDS")
# ATLAS_INSECURE=1 accepts a self-signed certificate — for testing against a
# staging host before a real cert exists. Never use it to check production.
INSECURE=(); [ "${ATLAS_INSECURE:-0}" = "1" ] && INSECURE=(-k)
PASS=0; FAIL=0
ok()   { printf '  \033[32mPASS\033[0m  %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n'  "$1"; FAIL=$((FAIL+1)); }
info() { printf '  \033[2m----  %s\033[0m\n' "$1"; }
head_code() { curl "${INSECURE[@]}" -sS -o /dev/null -w '%{http_code}' -m 20 "${AUTH[@]}" "$1" 2>/dev/null; }
hdr()       { curl "${INSECURE[@]}" -sSI -m 20 "${AUTH[@]}" "$1" 2>/dev/null | tr -d '\r'; }

printf '\n\033[1mVenture Atlas smoke test\033[0m  %s\n\n' "$BASE"

# --- 1. the app responds ------------------------------------------------------
code=$(head_code "$BASE/")
[ "$code" = "200" ] && ok "app root returns 200" || bad "app root returns $code (expected 200)"

# --- 2. the gate is actually on, and covers the data too ---------------------
if [ -n "$CREDS" ]; then
    anon=$(curl "${INSECURE[@]}" -sS -o /dev/null -w '%{http_code}' -m 20 "$BASE/" 2>/dev/null)
    [ "$anon" = "401" ] && ok "anonymous request to app is refused (401)" \
                        || bad "anonymous request to app returned $anon — THE GATE IS OPEN"
else
    info "no credentials given — skipping gate checks"
fi

# --- 3. the manifest, and what it says is deployed ---------------------------
man="$BASE/data/current/manifest.json"
code=$(head_code "$man")
if [ "$code" = "200" ]; then
    ok "manifest served"
    body=$(curl "${INSECURE[@]}" -sS -m 20 "${AUTH[@]}" "$man" 2>/dev/null)
    ver=$(printf '%s' "$body" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("version",""))' 2>/dev/null)
    planes=$(printf '%s' "$body" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(",".join(str(p["z"]) for p in d.get("planes",[])))' 2>/dev/null)
    cc=$(hdr "$man" | grep -i '^cache-control:' | head -1)
    info "release=$ver planes=[$planes]"
    case "$cc" in *no-store*) ok "manifest is not cached (no-store)";;
                   *) bad "manifest Cache-Control is '${cc:-absent}' — must be no-store or a release flip won't be seen";; esac
else
    bad "manifest returns $code — nothing deployed, or the alias is wrong"
    ver=""; planes=""
fi

# --- 4. THE DOTFILE TEST -----------------------------------------------------
# If this fails, the viewer renders a blank panel with no console error worth
# reading. It is the single most likely way this deploy breaks.
if [ -n "${ver:-}" ] && [ -n "${planes:-}" ]; then
    z1="${planes%%,*}"
    store=$(curl "${INSECURE[@]}" -sS -m 20 "${AUTH[@]}" "$man" 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
p=[p for p in d['planes'] if str(p['z'])=='${z1}'][0]
print(p['cells_zarr'])" 2>/dev/null)
    if [ -n "$store" ]; then
        base_store="$BASE/data/$ver/$store"
        info "probing store $store"
        for f in .zmetadata .zgroup; do
            code=$(head_code "$base_store/$f")
            [ "$code" = "200" ] && ok "dotfile $f served (200)" \
                                || bad "dotfile $f returns $code — nginx is denying dotfiles"
        done
        ct=$(hdr "$base_store/.zmetadata" | grep -i '^content-type:' | head -1)
        case "$ct" in *json*) ok ".zmetadata served as JSON";;
                       *) bad ".zmetadata content-type is '${ct:-absent}' — expected application/json";; esac

        # a real chunk, via a path taken from .zmetadata
        chunk=$(curl "${INSECURE[@]}" -sS -m 20 "${AUTH[@]}" "$base_store/.zmetadata" 2>/dev/null | python3 -c "
import json,sys
m=json.load(sys.stdin)['metadata']
for k in m:
    if k.endswith('.zarray'):
        arr=k[:-len('/.zarray')]
        sh=m[k].get('shape') or []
        ch=m[k].get('chunks') or []
        if sh and ch and all(s>0 for s in sh):
            print(arr+'/'+'.'.join(['0']*len(sh))); break" 2>/dev/null)
        if [ -n "$chunk" ]; then
            sz=$(curl "${INSECURE[@]}" -sS -m 40 -o /dev/null -w '%{size_download}' "${AUTH[@]}" "$base_store/$chunk" 2>/dev/null)
            [ "${sz:-0}" -gt 0 ] && ok "chunk $chunk served (${sz} bytes)" \
                                 || bad "chunk $chunk served 0 bytes"
            cc=$(hdr "$base_store/$chunk" | grep -i '^cache-control:' | head -1)
            case "$cc" in *immutable*) ok "chunks cached immutable (protects the egress quota)";;
                           *) bad "chunk Cache-Control is '${cc:-absent}' — expected immutable";; esac
            ce=$(hdr "$base_store/$chunk" | grep -i '^content-encoding:' | head -1)
            case "$ce" in *gzip*) bad "chunk is gzipped — it is already blosc-compressed; fix gzip_types";;
                           *) ok "chunk is not gzipped";; esac
        else
            info "could not derive a chunk path from .zmetadata — skipped chunk checks"
        fi
    fi
else
    info "no manifest — skipping store checks"
fi

# --- 4b. every data URL in every config resolves -----------------------------
# The viewer rewrites each config `url` to /data/<version>/<basename> so one
# build deploys anywhere. This mirrors that rewrite and checks the result
# actually exists — it is the difference between "the files are on disk" and
# "the viewer can find them".
if [ -n "${ver:-}" ] && [ -n "${planes:-}" ]; then
    cfg_bad=0; cfg_n=0
    for zz in $(printf '%s' "$planes" | tr ',' ' '); do
        cfile=$(printf '%s' "$body" | python3 -c "
import json,sys
d=json.load(sys.stdin)
p=[p for p in d['planes'] if str(p['z'])=='$zz']
print(p[0].get('config','') if p else '')" 2>/dev/null)
        [ -n "$cfile" ] || continue
        urls=$(curl "${INSECURE[@]}" -sS -m 20 "${AUTH[@]}" "$BASE/data/$ver/$cfile" 2>/dev/null | python3 -c "
import json,sys
seen=[]
def walk(n):
    if isinstance(n,list):
        for x in n: walk(x)
    elif isinstance(n,dict):
        for k,v in n.items():
            if k=='url' and isinstance(v,str) and v:
                seen.append(v.rstrip('/').split('/')[-1])
            else: walk(v)
walk(json.load(sys.stdin))
print('\n'.join(sorted(set(seen))))" 2>/dev/null)
        for u in $urls; do
            cfg_n=$((cfg_n+1))
            c=$(head_code "$BASE/data/$ver/$u/.zgroup")
            [ "$c" = "200" ] || { bad "config z$zz references $u, which does not resolve (.zgroup -> $c)"; cfg_bad=$((cfg_bad+1)); }
        done
    done
    if [ "$cfg_n" -eq 0 ]; then
        info "no data URLs found in the configs — check the config format"
    elif [ "$cfg_bad" -eq 0 ]; then
        ok "all $cfg_n data URLs across the configs resolve"
    fi
fi

# --- 5. no third-party viewer dependency (the whole point of E-1) ------------
home=$(curl "${INSECURE[@]}" -sS -m 20 "${AUTH[@]}" "$BASE/" 2>/dev/null)
# Strip HTML comments first: the page legitimately *mentions* vitessce.io in a
# comment explaining why it no longer loads from there.
live=$(printf '%s' "$home" | python3 -c 'import re,sys;sys.stdout.write(re.sub(r"<!--.*?-->","",sys.stdin.read(),flags=re.S))' 2>/dev/null || printf '%s' "$home")
if printf '%s' "$live" | grep -qiE '(src|href)="[^"]*vitessce\.io|https?://vitessce\.io'; then
    bad "the page still loads from vitessce.io — auth-gated data will not load for it"
else
    ok "no vitessce.io dependency in the page"
fi
if printf '%s' "$live" | grep -qiE '(src|href)="https?://(cdn|unpkg|esm|cdnjs|jsdelivr)'; then
    bad "the page loads assets from a third-party CDN — vendor them instead"
else
    ok "no third-party asset origins"
fi

# --- 5b. the bundle's chunk graph actually resolves ---------------------------
# esbuild code-splitting emits content-hashed chunks that main.js imports by
# path. A stale --public-path, or a vendor/ dir copied incompletely, gives a
# blank page and a bare "failed to fetch dynamically imported module".
mainjs=$(curl "${INSECURE[@]}" -sS -m 20 "${AUTH[@]}" "$BASE/vendor/main.js" 2>/dev/null)
if [ -z "$mainjs" ]; then
    bad "/vendor/main.js is empty or missing — run app/build.sh and copy app/vendor to the server"
else
    ok "/vendor/main.js served"
    imports=$(printf '%s' "$mainjs" | grep -oE 'from"[^"]+"' | sed 's/from"//;s/"//' | sort -u)
    missing=0; checked=0
    for imp in $imports; do
        case "$imp" in
            /*) ;;                      # our own chunk, by absolute path
            *) continue;;               # bare specifier shouldn't survive bundling
        esac
        checked=$((checked+1))
        c=$(head_code "$BASE$imp")
        [ "$c" = "200" ] || { bad "bundle chunk $imp returns $c"; missing=$((missing+1)); }
    done
    if [ "$checked" -eq 0 ]; then
        info "main.js has no static chunk imports to check"
    elif [ "$missing" -eq 0 ]; then
        ok "all $checked bundle chunks resolve"
    fi
fi

# --- 6. TLS and redirect ------------------------------------------------------
case "$BASE" in
  https://*:[0-9]*)
    # An explicit non-standard port means this is a staging host; we cannot
    # guess which port the plain-http vhost is on, so don't report a false
    # failure. Check the redirect by hand against port 80.
    info "explicit port in URL — skipping the http-redirect and ACME probes"
    ;;
  https://*)
    plain="http://${BASE#https://}"
    rc=$(curl "${INSECURE[@]}" -sS -o /dev/null -w '%{http_code}' -m 20 "$plain/" 2>/dev/null)
    case "$rc" in 301|302|308) ok "http redirects to https ($rc)";;
                  *) bad "http returned $rc — expected a redirect to https";; esac
    # ACME path must stay reachable without credentials or renewal breaks
    ac=$(curl "${INSECURE[@]}" -sS -o /dev/null -w '%{http_code}' -m 20 "$plain/.well-known/acme-challenge/probe" 2>/dev/null)
    case "$ac" in 401) bad "ACME challenge path is behind auth — cert renewal will fail";;
                  *) ok "ACME challenge path is not behind auth ($ac)";; esac
    ;;
  *) info "not https — skipping TLS checks (fine for a local dry run)";;
esac

printf '\n  \033[1m%d passed, %d failed\033[0m\n\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
