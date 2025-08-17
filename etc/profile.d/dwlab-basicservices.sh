#!/bin/bash
#

DWLAB_HOME="/opt/dwlab"
# shellcheck shell=sh
if [ ! -d "$DWLAB_HOME" ]; then
  echo "DW-Lab: The directory '$DWLAB_HOME' does not exist"
else
  export DWLAB_HOME
  # Expand $PATH to include the directory where DW-Lab application extensions go.
  dwlab_bin_path="$DWLAB_HOME/dwlab-basicservices/bin"

  if [ -d "$dwlab_bin_path" ]; then
    if [ -n "${PATH##*${dwlab_bin_path}}" ] && [ -n "${PATH##*${dwlab_bin_path}:*}" ]; then
        export PATH="$PATH:${dwlab_bin_path}"
    fi
  fi

  
  
fi

