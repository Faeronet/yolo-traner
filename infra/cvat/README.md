# Local CVAT

Brings up a local [CVAT](https://github.com/cvat-ai/cvat) instance and mounts
`data/cvat_shared/` as `/home/django/share` so labelers can pick images
directly from the project.

## Prerequisites

* Docker Engine 24+ and Docker Compose v2 plugin
* `git` available on `PATH`
* A few GB of free disk for the CVAT containers and DB volume

## Usage

```bash
# 1. Start (clones/updates cvat-ai/cvat into infra/cvat/cvat_src on first run)
bash setup_cvat.sh up

# 2. Create the admin account (non-interactive if CVAT_SUPERUSER_PASSWORD is set in .env)
bash setup_cvat.sh create-superuser

# 3. Verify that the project's data/cvat_shared is mounted as /home/django/share
bash setup_cvat.sh check-share

# 4. Stop everything
bash setup_cvat.sh down
```

## Access from LAN, VPN or other subnets

Upstream CVAT’s Traefik rules use **`Host(${CVAT_HOST})`**, so opening
`http://<server-LAN-ip>:8080` did not route to the UI. This project overrides
routing so **API, UI and Grafana `/analytics`** accept **any Host header**:

* `infra/cvat/docker-compose.override.yml` — routers use `HostRegexp` so any
  `Host:` / IP works, with priorities so `/api/` still hits the backend.
* When **`CVAT_ANALYTICS_ANY_HOST=1`** (default), `setup_cvat.sh up` copies
  `infra/cvat/grafana_traefik_any_host.yml` over
  `cvat_src/components/analytics/grafana_conf.yml` after each upstream
  `git reset` (stock is saved as `grafana_conf.yml.bak.yolo-train`).

Docker still publishes **`8080/tcp` on all interfaces** (`0.0.0.0`), which is
the usual default mapping.

Firewall (example):

```bash
sudo ufw allow 8080/tcp comment 'CVAT'
```

Use a **strong** superuser password, VPN, or HTTPS reverse-proxy when the host
is reachable from untrusted networks.

## Environment

See project `.env.example`:

* **`CVAT_ANALYTICS_ANY_HOST`** — `1`: patch Grafana routing for any Host;
  `0`: keep stock Grafana rules (then set **`CVAT_HOST`** to the same name or IP
  the browser uses).
* **`CVAT_PORT`** — informational in our scripts; Traefik’s host port is fixed
  in CVAT’s upstream `docker-compose.yml` (8080) unless you change it there.

## What gets mounted

`docker-compose.override.yml` defines a bind volume `cvat_share` that points
to the host path `${CVAT_SHARE_PATH}` (defaults to
`<project_root>/data/cvat_shared`). The volume is mounted into:

* `cvat_server`
* `cvat_worker_import`
* `cvat_worker_export`
* `cvat_worker_annotation`
* `cvat_worker_quality_reports`

Inside CVAT, when creating a task you can choose **"Share folder"** as the
source and pick subdirectories under `/home/django/share/` such as
`page_classification/` or `drawing_segmentation/`.

## Where data lives

The CVAT database, files, logs and event volumes are created locally as
Docker volumes inside `infra/cvat/cvat_src/`. They are gitignored. Removing
those volumes deletes labels, so back up regularly.
