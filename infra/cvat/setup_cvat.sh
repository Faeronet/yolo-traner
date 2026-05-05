#!/usr/bin/env bash
# =============================================================================
# Helper that brings a local CVAT up/down using the official upstream repo
# and our docker-compose.override.yml.
#
# Subcommands:
#   up                    -> clone/pull cvat-ai/cvat, start containers
#   down                  -> stop containers
#   create-superuser      -> create admin user inside the cvat_server container
#   check-share           -> verify that data/cvat_shared is mounted as /home/django/share
# =============================================================================

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${HERE}/../.." && pwd)"
CVAT_SRC_DIR="${HERE}/cvat_src"
OVERRIDE_FILE="${HERE}/docker-compose.override.yml"

# Load project .env if present so CVAT_HOST / CVAT_PORT / CVAT_SHARE_PATH come through.
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    . "${PROJECT_ROOT}/.env"
    set +a
fi

CVAT_HOST="${CVAT_HOST:-localhost}"
CVAT_PORT="${CVAT_PORT:-8080}"
CVAT_SHARE_PATH="${CVAT_SHARE_PATH:-${PROJECT_ROOT}/data/cvat_shared}"
CVAT_SUPERUSER_USERNAME="${CVAT_SUPERUSER_USERNAME:-admin}"
CVAT_SUPERUSER_EMAIL="${CVAT_SUPERUSER_EMAIL:-admin@example.com}"
CVAT_SUPERUSER_PASSWORD="${CVAT_SUPERUSER_PASSWORD:-}"
CVAT_ANALYTICS_ANY_HOST="${CVAT_ANALYTICS_ANY_HOST:-1}"

export CVAT_HOST CVAT_PORT CVAT_SHARE_PATH

_cmd_hint_lan_ips() {
    if command -v hostname >/dev/null 2>&1; then
        hostname -I 2>/dev/null | awk '{ for (i=1;i<=NF;i++) print $i }'
    fi
}

cmd_up() {
    mkdir -p "${CVAT_SHARE_PATH}"

    if [[ ! -d "${CVAT_SRC_DIR}/.git" ]]; then
        echo "Cloning cvat-ai/cvat into ${CVAT_SRC_DIR} ..."
        git clone --depth 1 https://github.com/cvat-ai/cvat.git "${CVAT_SRC_DIR}"
    else
        echo "Updating CVAT sources ..."
        git -C "${CVAT_SRC_DIR}" fetch --depth 1 origin
        git -C "${CVAT_SRC_DIR}" reset --hard origin/HEAD || true
    fi

    cp "${OVERRIDE_FILE}" "${CVAT_SRC_DIR}/docker-compose.override.yml"

    local grafana_upstream="${CVAT_SRC_DIR}/components/analytics/grafana_conf.yml"
    local grafana_any="${HERE}/grafana_traefik_any_host.yml"

    # Let UI/API (and Grafana) answer on any reachable Host/IP (Traefik routers).
    if [[ "${CVAT_ANALYTICS_ANY_HOST}" != "0" ]] && [[ -f "${grafana_any}" ]] && [[ -f "${grafana_upstream}" ]]; then
        cp "${grafana_upstream}" "${grafana_upstream}.bak.yolo-train"
        cp "${grafana_any}" "${grafana_upstream}"
        echo "Grafana Traefik route patched for any Host (CVAT_ANALYTICS_ANY_HOST=${CVAT_ANALYTICS_ANY_HOST})."
    elif [[ "${CVAT_ANALYTICS_ANY_HOST}" == "0" ]]; then
        echo "CVAT_ANALYTICS_ANY_HOST=0 → keeping upstream Grafana Host(\${CVAT_HOST}) routing."
        echo "Set CVAT_HOST in .env to the hostname/IP browsers use."
    fi

    echo "Starting CVAT (CVAT_HOST=${CVAT_HOST} port=${CVAT_PORT}, share=${CVAT_SHARE_PATH}) ..."
    echo "HTTPS Host header routing is permissive — open http(s)://<any-interface-ip>:${CVAT_PORT} from LAN/VPN/etc."
    pushd "${CVAT_SRC_DIR}" >/dev/null
    CVAT_HOST="${CVAT_HOST}" CVAT_VERSION=latest \
        docker compose -f docker-compose.yml -f docker-compose.override.yml up -d
    popd >/dev/null

    echo "CVAT publishes docker port ${CVAT_PORT} on all interfaces (0.0.0.0) by default."
    echo "Example URLs: http://${CVAT_HOST}:${CVAT_PORT}"
    while read -r ip; do
        [[ "${ip}" == "127.0.0.1" ]] && continue
        [[ -z "${ip}" ]] && continue
        echo "                 http://${ip}:${CVAT_PORT}"
    done < <(_cmd_hint_lan_ips)
    echo "Run 'bash setup_cvat.sh create-superuser' once it is healthy."
}

cmd_down() {
    if [[ ! -d "${CVAT_SRC_DIR}" ]]; then
        echo "CVAT sources not found at ${CVAT_SRC_DIR}; nothing to stop."
        return 0
    fi
    pushd "${CVAT_SRC_DIR}" >/dev/null
    docker compose -f docker-compose.yml -f docker-compose.override.yml down
    popd >/dev/null
}

cmd_create_superuser() {
    if [[ -n "${CVAT_SUPERUSER_PASSWORD}" ]]; then
        echo "Creating CVAT superuser '${CVAT_SUPERUSER_USERNAME}' non-interactively ..."
        docker exec -i cvat_server bash -lc \
            "DJANGO_SUPERUSER_USERNAME='${CVAT_SUPERUSER_USERNAME}' \
             DJANGO_SUPERUSER_EMAIL='${CVAT_SUPERUSER_EMAIL}' \
             DJANGO_SUPERUSER_PASSWORD='${CVAT_SUPERUSER_PASSWORD}' \
             python manage.py createsuperuser --no-input"
    else
        echo "CVAT_SUPERUSER_PASSWORD is empty; opening interactive prompt ..."
        docker exec -it cvat_server python manage.py createsuperuser
    fi
}

cmd_check_share() {
    if ! docker ps --format '{{.Names}}' | grep -q '^cvat_server$'; then
        echo "ERROR: cvat_server container is not running. Run 'bash setup_cvat.sh up' first." >&2
        exit 2
    fi
    echo "Inside cvat_server, /home/django/share contains:"
    docker exec cvat_server ls -la /home/django/share
}

case "${1:-help}" in
    up)               cmd_up ;;
    down)             cmd_down ;;
    create-superuser) cmd_create_superuser ;;
    check-share)      cmd_check_share ;;
    *)
        cat <<USAGE
Usage: $0 {up|down|create-superuser|check-share}

  up                Start local CVAT (clones/updates cvat-ai/cvat as needed).
  down              Stop local CVAT.
  create-superuser  Create the admin user inside the cvat_server container.
  check-share       Verify that data/cvat_shared is mounted as /home/django/share.

Environment (read from project .env when present):
  CVAT_HOST=localhost          # Grafana advertised URL / docs; routers accept any Host
  CVAT_PORT=8080
  CVAT_ANALYTICS_ANY_HOST=1   # Patch Grafana routing for LAN IP/DNS access (set 0 to keep stock CVAT_HOST-only)
  CVAT_SHARE_PATH=/home/.../yolo-train/data/cvat_shared
  CVAT_SUPERUSER_USERNAME=admin
  CVAT_SUPERUSER_EMAIL=admin@example.com
  CVAT_SUPERUSER_PASSWORD=...
USAGE
        ;;
esac
