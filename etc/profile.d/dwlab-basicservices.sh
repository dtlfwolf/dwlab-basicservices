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

  ## Expand $PYTHONPATH to include the directory where DW-Lab application extensions go.
  #dwlab_python_path="$DWLAB_HOME/dwlab-basicservices/src"
  #if [ -d "$dwlab_python_path" ]; then
  #  if [ -n "${PYTHONPATH##*${dwlab_python_path}}" ] && [ -n "${PYTHONPATH##*${dwlab_python_path}:*}" ]; then
  #    export PYTHONPATH="$PYTHONPATH:${dwlab_python_path}"
  #  else
  #    if [ -z $PYTHONPATH ]; then
  #      export PYTHONPATH="${dwlab_python_path}"
  #    fi
  #  fi
  #fi
fi

