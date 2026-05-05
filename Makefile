# =============================================================================
# yolo-train Makefile
# =============================================================================
# Strict zone separation:
#   data/           -> only data
#   runs/           -> only training experiments (NOT production)
#   model_registry/ -> only verified production-ready weights
#   model_packages/ -> only portable production archives
# =============================================================================

SHELL          := /bin/bash
.SHELLFLAGS    := -eu -o pipefail -c
.DEFAULT_GOAL  := help

PYTHON         ?= python3
PIP            ?= $(PYTHON) -m pip
PROJECT_ROOT   := $(abspath $(CURDIR))
SCRIPTS        := $(PROJECT_ROOT)/scripts
SRC            := $(PROJECT_ROOT)/src

export PYTHONPATH := $(SRC):$(PYTHONPATH)

# Default archive name (override via `make prepare ARCHIVE="..."`).
ARCHIVE        ?= ПДФ.rar

# Default version for promote/package (override via VERSION=v1.2.3).
VERSION        ?= v0.0.0

# Default training run paths used by promote-* targets (override via RUN=...).
RUN            ?=

# Default destination for install-models-to-project.
TARGET         ?= ../drawing2dxf

# Load .env if present
ifneq (,$(wildcard .env))
include .env
export
endif

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------
.PHONY: help
help: ## Show this help
	@printf "\n\033[1myolo-train\033[0m available targets:\n\n"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_.-]+:.*?## / {printf "  \033[36m%-32s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf "\n"

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
.PHONY: install
install: ## Install Python dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

.PHONY: clean
clean: ## Remove caches and temporary files (does NOT touch data/, runs/, registry, packages)
	$(PYTHON) $(SCRIPTS)/clean.py

# -----------------------------------------------------------------------------
# Data preparation
# -----------------------------------------------------------------------------
.PHONY: prepare
prepare: ## Prepare data: extract archive, render PDFs, build inventory, populate cvat_shared. Usage: make prepare ARCHIVE="ПДФ.rar"
	$(PYTHON) $(SCRIPTS)/extract_archives.py --archive "$(ARCHIVE)"
	$(PYTHON) $(SCRIPTS)/extract_pdf_pages.py
	$(PYTHON) $(SCRIPTS)/normalize_images.py
	$(PYTHON) $(SCRIPTS)/make_inventory.py
	$(PYTHON) $(SCRIPTS)/make_thumbnails.py

# -----------------------------------------------------------------------------
# CVAT (local Docker)
# -----------------------------------------------------------------------------
.PHONY: cvat-up
cvat-up: ## Start CVAT locally via docker compose
	cd infra/cvat && bash setup_cvat.sh up

.PHONY: cvat-down
cvat-down: ## Stop local CVAT
	cd infra/cvat && bash setup_cvat.sh down

.PHONY: cvat-create-superuser
cvat-create-superuser: ## Create CVAT superuser (or print instruction)
	cd infra/cvat && bash setup_cvat.sh create-superuser

.PHONY: cvat-prepare-share
cvat-prepare-share: ## Verify that data/cvat_shared is mounted as /home/django/share
	cd infra/cvat && bash setup_cvat.sh check-share

.PHONY: cvat-create-tasks
cvat-create-tasks: ## (Optional) Create CVAT projects/tasks via REST API
	$(PYTHON) $(SCRIPTS)/create_cvat_tasks.py

.PHONY: cvat-export
cvat-export: ## (Optional) Pull annotations from CVAT API into data/cvat_exports
	$(PYTHON) $(SCRIPTS)/export_cvat_annotations.py

# -----------------------------------------------------------------------------
# Dataset construction
# -----------------------------------------------------------------------------
.PHONY: build-page-cls-dataset
build-page-cls-dataset: ## Build YOLO classification dataset from CVAT export
	$(PYTHON) $(SCRIPTS)/build_page_cls_dataset.py

.PHONY: build-seg-dataset
build-seg-dataset: ## Build YOLO segmentation dataset from CVAT export
	$(PYTHON) $(SCRIPTS)/build_seg_dataset_from_cvat.py

.PHONY: tile-seg-dataset
tile-seg-dataset: ## Slice segmentation dataset into tiles
	$(PYTHON) $(SCRIPTS)/tile_seg_dataset.py

.PHONY: validate-datasets
validate-datasets: ## Run integrity checks on built datasets
	$(PYTHON) $(SCRIPTS)/validate_dataset.py

# -----------------------------------------------------------------------------
# Training (writes ONLY to runs/, NOT to model_registry/)
# -----------------------------------------------------------------------------
.PHONY: train-page-cls
train-page-cls: ## Train YOLO11s-cls (results go ONLY to runs/page_cls/)
	$(PYTHON) $(SCRIPTS)/train_page_cls.py

.PHONY: train-drawing-seg
train-drawing-seg: ## Train YOLO11m-seg (results go ONLY to runs/drawing_seg/)
	$(PYTHON) $(SCRIPTS)/train_drawing_seg.py

# -----------------------------------------------------------------------------
# Promotion runs/ -> model_registry/  (requires explicit RUN=... and VERSION=...)
# -----------------------------------------------------------------------------
.PHONY: promote-page-cls
promote-page-cls: ## Promote a run to model_registry/page_router. Usage: make promote-page-cls RUN=runs/page_cls/exp1 VERSION=v1.0.0
	@if [ -z "$(RUN)" ]; then echo "ERROR: RUN=<path-to-run> required"; exit 1; fi
	$(PYTHON) $(SCRIPTS)/promote_to_registry.py --model page_router --run "$(RUN)" --version "$(VERSION)"

.PHONY: promote-drawing-seg
promote-drawing-seg: ## Promote a run to model_registry/drawing_segmenter. Usage: make promote-drawing-seg RUN=runs/drawing_seg/exp1 VERSION=v1.0.0
	@if [ -z "$(RUN)" ]; then echo "ERROR: RUN=<path-to-run> required"; exit 1; fi
	$(PYTHON) $(SCRIPTS)/promote_to_registry.py --model drawing_segmenter --run "$(RUN)" --version "$(VERSION)"

# -----------------------------------------------------------------------------
# Packaging model_registry/ -> model_packages/ (NO datasets, NO raw data)
# -----------------------------------------------------------------------------
.PHONY: package-models
package-models: ## Build production-ready tarballs from model_registry/. Usage: make package-models VERSION=v1.0.0
	$(PYTHON) $(SCRIPTS)/build_package.py --version "$(VERSION)"

# -----------------------------------------------------------------------------
# Install models into the consuming project (drawing2dxf)
# -----------------------------------------------------------------------------
.PHONY: install-models-to-project
install-models-to-project: ## Copy current/ models into drawing2dxf. Usage: make install-models-to-project TARGET=../drawing2dxf
	$(PYTHON) $(SCRIPTS)/install_models_to_project.py --target "$(TARGET)"

# -----------------------------------------------------------------------------
# Inference helpers (manual)
# -----------------------------------------------------------------------------
.PHONY: predict-page-cls
predict-page-cls: ## Run page_router predictions (writes to runs/predictions/)
	$(PYTHON) $(SCRIPTS)/predict_page_cls.py

.PHONY: predict-drawing-seg
predict-drawing-seg: ## Run drawing_segmenter predictions (writes to runs/predictions/)
	$(PYTHON) $(SCRIPTS)/predict_drawing_seg.py

.PHONY: active-learning
active-learning: ## Suggest pages for next labeling round
	$(PYTHON) $(SCRIPTS)/active_learning_candidates.py

# -----------------------------------------------------------------------------
# Quality
# -----------------------------------------------------------------------------
.PHONY: lint
lint: ## Run ruff
	ruff check src scripts tests

.PHONY: test
test: ## Run pytest
	pytest
