#!/bin/bash

set -euo pipefail

# Explicitly load the base DW-Lab shell helpers for the current shell context.
if [ -r /etc/profile.d/dwlab-basicservices.sh ]; then
  # shellcheck disable=SC1091
  source /etc/profile.d/dwlab-basicservices.sh
fi
