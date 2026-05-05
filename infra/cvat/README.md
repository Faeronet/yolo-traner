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

The default exposed URL is `http://localhost:8080`. Override with `CVAT_HOST`
and `CVAT_PORT` in the project `.env`.

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
