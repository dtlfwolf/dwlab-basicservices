SHELL := /bin/bash

ROOT := $(abspath $(CURDIR))
DWLAB_HELPERS_ROOT ?= $(abspath $(ROOT)/../dwlab-helpers)
DWLAB_ARTIFACTS_ROOT ?= $(abspath $(ROOT)/../dwlab-packages)
PACKAGES_DIR ?= $(DWLAB_ARTIFACTS_ROOT)
BINARY_BUILDER := $(DWLAB_HELPERS_ROOT)/build-dwlab-binary-package.sh
PACKAGE_NAME := dwlab-basicservices

.PHONY: help build clean inspect show-package

help:
	@echo "Targets for $(PACKAGE_NAME):"
	@echo "  make build        Build the Debian package into $(PACKAGES_DIR)"
	@echo "  make clean        Remove package build staging under /tmp on next run"
	@echo "  make inspect      List generated package files"
	@echo "  make show-package Show package metadata source"

build:
	$(BINARY_BUILDER) "$(ROOT)" "$(PACKAGES_DIR)"

clean:
	@echo "DW-Lab: No local in-tree build artifacts to remove for $(PACKAGE_NAME)."
	@echo "DW-Lab: Staging is recreated automatically in /tmp by the helper script."

inspect:
	@ls -1 "$(PACKAGES_DIR)"/$(PACKAGE_NAME)_*.deb 2>/dev/null || echo "No package built yet."

show-package:
	@sed -n '1,20p' DEBIAN/control
