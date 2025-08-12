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

  # Activate the Python virtual environment if it exists
  if [ -f /opt/dwlab/venv/bin/activate ]; then
      # shellcheck disable=SC1091
      echo "DW-Lab: Sourcing the Python virtual environment at /opt/dwlab/venv/. "
      . /opt/dwlab/venv/bin/activate
  else
      echo "DW-Lab: /opt/dwlab/venv/bin/activate not found, cannot source it."
      echo "DW-Lab: Please ensure that the Python virtual environment is set up correctly."
  fi
  
  
fi

