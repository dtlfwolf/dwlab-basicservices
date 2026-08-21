#!/bin/bash

DWLAB_HOME="/opt/dwlab"
dwlab_bin_path="$DWLAB_HOME/dwlab-basicservices/bin"

if [ -d "$DWLAB_HOME" ]; then
  export DWLAB_HOME
fi

if [ -d "$dwlab_bin_path" ]; then
  case ":$PATH:" in
    *":$dwlab_bin_path:"*) ;;
    *) export PATH="$PATH:$dwlab_bin_path" ;;
  esac
fi
