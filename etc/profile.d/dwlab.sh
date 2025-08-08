#!/bin/bash
#

# Source all DW-Lab components from /etc/profile.d/dwlab-*.sh
for component in /etc/profile.d/dwlab-*.sh; do
  if [ -r "$component" ]; then
    source "$component"
  fi
done

