#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

readonly ACCOUNT_HOME="${HOME:?HOME is not set}"
readonly RELEASE_ZIP="${1:-$ACCOUNT_HOME/mediprofit-release.zip}"
readonly WEB_ROOT="$ACCOUNT_HOME/public_html"
readonly API_ROOT="$WEB_ROOT/api-hms"
readonly FRONTEND_ROOT="$WEB_ROOT/hms"
readonly FRONTEND_ASSET_ROOT="$ACCOUNT_HOME/mediprofit-assets"
readonly API_ENV="$ACCOUNT_HOME/.hms-api.env"
readonly STAMP="$(date +%Y%m%d-%H%M%S)"
readonly STAGE="$ACCOUNT_HOME/.mediprofit-stage-$STAMP"
readonly API_BACKUP="$ACCOUNT_HOME/api-hms-backup-$STAMP"
readonly FRONTEND_BACKUP="$ACCOUNT_HOME/hms-backup-$STAMP"

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$1"; }
fail() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }
cleanup() {
  if [ -d "$STAGE" ]; then
    find "$STAGE" -mindepth 1 -delete 2>/dev/null || true
    rmdir "$STAGE" 2>/dev/null || true
  fi
}
trap cleanup EXIT

log "Preflight"
[ "$ACCOUNT_HOME" = "/home/digidriv" ] || fail "Unexpected account home: $ACCOUNT_HOME"
[ -f "$RELEASE_ZIP" ] || fail "Missing release ZIP: $RELEASE_ZIP"
[ -f "$API_ENV" ] || fail "Missing production configuration: $API_ENV"
[ -d "$WEB_ROOT" ] || fail "Missing cPanel web root: $WEB_ROOT"
[ ! -L "$API_ROOT" ] || fail "$API_ROOT is a symlink; manual review required."
[ ! -L "$FRONTEND_ROOT" ] || fail "$FRONTEND_ROOT is a symlink; manual review required."
command -v unzip >/dev/null 2>&1 || fail "unzip is unavailable."
command -v curl >/dev/null 2>&1 || fail "curl is unavailable."

for required in \
  api-hms/passenger_wsgi.py \
  api-hms/requirements.txt \
  api-hms/alembic.ini \
  api-hms/app/main.py \
  api-hms/scripts/reconcile_schema.py \
  hms/index.html \
  hms/main.js \
  hms/assets/app-config.json \
  hms/.htaccess
do
  unzip -Z1 "$RELEASE_ZIP" | awk -v item="$required" '$0==item{found=1} END{exit !found}' || fail "Release ZIP is missing $required"
done

PYTHON_BIN=""
PYTHON_CANDIDATES="$(find -L "$ACCOUNT_HOME/virtualenv" -maxdepth 8 \( -type f -o -type l \) -path '*/bin/python*' 2>/dev/null | sort || true)"
while IFS= read -r candidate; do
  [ -n "$candidate" ] || continue
  if [ -x "$candidate" ]; then
    case "$candidate" in
      */public_html/api-hms/*) PYTHON_BIN="$candidate"; break ;;
      *) [ -z "$PYTHON_BIN" ] && PYTHON_BIN="$candidate" ;;
    esac
  fi
done <<PYTHON_PATHS
$PYTHON_CANDIDATES
PYTHON_PATHS
[ -n "$PYTHON_BIN" ] || fail "No cPanel Python environment found. Create Setup Python App for public_html/api-hms first."
printf 'Using Python: %s\n' "$PYTHON_BIN"

log "Extracting and validating complete release"
mkdir "$STAGE"
unzip -q "$RELEASE_ZIP" -d "$STAGE"
grep -Fq 'https://api-hms.digidrivetechnology.com/api/v1' "$STAGE/hms/assets/app-config.json" || fail "Frontend API URL is incorrect."
grep -q '^Options -Indexes' "$STAGE/hms/.htaccess" || fail "Frontend .htaccess is invalid."
sed -i 's/^Options -Indexes.*$/Options -Indexes +SymLinksIfOwnerMatch/' "$STAGE/hms/.htaccess"
cp "$API_ENV" "$STAGE/api-hms/.env"
chmod 600 "$STAGE/api-hms/.env"
{
  printf 'PassengerEnabled On\n'
  printf 'PassengerAppRoot "%s"\n' "$API_ROOT"
  printf 'PassengerBaseURI "/"\n'
  printf 'PassengerAppType wsgi\n'
  printf 'PassengerStartupFile passenger_wsgi.py\n'
  printf 'PassengerPython "%s"\n' "$PYTHON_BIN"
} > "$STAGE/api-hms/.htaccess"

log "Installing API dependencies"
"$PYTHON_BIN" -m pip install --disable-pip-version-check -r "$STAGE/api-hms/requirements.txt"
"$PYTHON_BIN" -m compileall -q "$STAGE/api-hms/app" "$STAGE/api-hms/passenger_wsgi.py" "$STAGE/api-hms/scripts"
find "$STAGE/api-hms" "$STAGE/hms" -type d -exec chmod 755 {} \;
find "$STAGE/api-hms" "$STAGE/hms" -type f -exec chmod 644 {} \;
chmod 600 "$STAGE/api-hms/.env"

log "Securing frontend bundle outside public_html"
mkdir -p "$FRONTEND_ASSET_ROOT"
chmod 755 "$FRONTEND_ASSET_ROOT"
readonly FRONTEND_BUNDLE="$FRONTEND_ASSET_ROOT/main-$STAMP.js"
mv "$STAGE/hms/main.js" "$FRONTEND_BUNDLE"
chmod 644 "$FRONTEND_BUNDLE"

log "Backing up current document roots"
[ -d "$API_ROOT" ] && mv "$API_ROOT" "$API_BACKUP"
[ -d "$FRONTEND_ROOT" ] && mv "$FRONTEND_ROOT" "$FRONTEND_BACKUP"

log "Publishing API and frontend"
if ! mv "$STAGE/api-hms" "$API_ROOT"; then
  [ -d "$API_BACKUP" ] && mv "$API_BACKUP" "$API_ROOT"
  [ -d "$FRONTEND_BACKUP" ] && mv "$FRONTEND_BACKUP" "$FRONTEND_ROOT"
  fail "Could not publish API; backups restored."
fi
if ! mv "$STAGE/hms" "$FRONTEND_ROOT"; then
  find "$API_ROOT" -mindepth 1 -delete 2>/dev/null || true
  rmdir "$API_ROOT" 2>/dev/null || true
  [ -d "$API_BACKUP" ] && mv "$API_BACKUP" "$API_ROOT"
  [ -d "$FRONTEND_BACKUP" ] && mv "$FRONTEND_BACKUP" "$FRONTEND_ROOT"
  fail "Could not publish frontend; backups restored."
fi
if ! ln -s "$FRONTEND_BUNDLE" "$FRONTEND_ROOT/main.js"; then
  find "$FRONTEND_ROOT" -mindepth 1 -delete 2>/dev/null || true
  rmdir "$FRONTEND_ROOT" 2>/dev/null || true
  [ -d "$API_BACKUP" ] && mv "$API_BACKUP" "$API_ROOT"
  [ -d "$FRONTEND_BACKUP" ] && mv "$FRONTEND_BACKUP" "$FRONTEND_ROOT"
  fail "Could not link the external frontend bundle; backups restored."
fi

log "Reconciling database migrations"
(
  cd "$API_ROOT"
  current_revision="$("$PYTHON_BIN" -m alembic current 2>/dev/null | awk 'NF { value=$1 } END { print value }')"
  head_revision="$("$PYTHON_BIN" -m alembic heads 2>/dev/null | awk 'NF { value=$1 } END { print value }')"
  if [ -n "$current_revision" ] && [ "$current_revision" = "$head_revision" ]; then
    printf 'Database already at Alembic head %s; migration check skipped.\n' "$head_revision"
  else
    printf 'Database revision %s requires reconciliation to %s.\n' "${current_revision:-unknown}" "${head_revision:-unknown}"
    "$PYTHON_BIN" scripts/reconcile_schema.py
  fi
)

log "Restarting cPanel Passenger"
mkdir -p "$API_ROOT/tmp"
touch "$API_ROOT/tmp/restart.txt"

log "Checking production endpoints"
api_status=""
for attempt in 1 2 3 4 5; do
  api_status="$(curl -L -sS -o /dev/null --max-time 20 -w '%{http_code}' 'https://api-hms.digidrivetechnology.com/health/live' || true)"
  [ "$api_status" = "200" ] && break
  sleep 3
done
frontend_status="$(curl -L -sS -o /dev/null --max-time 20 -w '%{http_code}' 'https://mediprofit.digidrivetechnology.com/' || true)"
bundle_status="$(curl -L -sS -o /dev/null --max-time 30 -w '%{http_code} %{content_type} %{size_download}' "https://mediprofit.digidrivetechnology.com/main.js?v=$STAMP" || true)"
[ "$api_status" = "200" ] || fail "API health returned HTTP ${api_status:-ERR}."
[ "$frontend_status" = "200" ] || fail "Frontend returned HTTP ${frontend_status:-ERR}."
case "$bundle_status" in
  "200 application/javascript "*|"200 text/javascript "*) ;;
  *) fail "Frontend bundle validation failed: ${bundle_status:-ERR}." ;;
esac
bundle_bytes="${bundle_status##* }"
[ "${bundle_bytes:-0}" -gt 100000 ] 2>/dev/null || fail "Frontend bundle is unexpectedly small: ${bundle_bytes:-0} bytes."

printf '\nDeployment successful.\n'
printf 'API: https://api-hms.digidrivetechnology.com/health/live\n'
printf 'Frontend: https://mediprofit.digidrivetechnology.com/#/auth/login\n'
printf 'External frontend bundle: %s\n' "$FRONTEND_BUNDLE"
[ -d "$API_BACKUP" ] && printf 'API backup: %s\n' "$API_BACKUP"
[ -d "$FRONTEND_BACKUP" ] && printf 'Frontend backup: %s\n' "$FRONTEND_BACKUP"
