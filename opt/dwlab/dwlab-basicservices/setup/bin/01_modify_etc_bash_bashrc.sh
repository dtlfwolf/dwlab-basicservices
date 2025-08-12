#!/bin/bash
#
#- Copyright:
#
# Company    = "DW-Lab GmbH"
# Department = "checkmk"
# Creation   = "07-Aug-2025"
# Version    = "1.0"
# Author     = "Detlef Wolf"
#
# Usage:  installation/bin/00_python3_runtime_venv.sh
#
# Description:
#
# Parameters  :
#  <none>
#
# References  :
#       Name      Type      Short description
#      ------------------------------------------------------------
#       <none>
#
# Changes :
# 07-Aug-2025  D. Wolf       - Creation

thisScript=$0

echo 'DW-Lab: ************************************************************************************************************'
echo 'DW-Lab: '$thisScript
echo 'DW-Lab: ************************************************************************************************************'
# -------------------------------------------------------------------------------
# Append activation dwlab Environment /etc/bash.bashrc for non-interactive shells
# This is needed to ensure that the dwlab venv is activated in non-interactive shells
# This is a workaround for the fact that /etc/profile.d/dwlab-basicservices.sh
# is not sourced in non-interactive shells by default.
# This script should be run as root to modify /etc/bash.bashrc
# It appends a snippet to /etc/bash.bashrc that activates the dwlab venv
# when an interactive shell is started.
# The snippet checks if /usr/local/bin/dwlab.sh exists and sources it.
# If the file does not exist, it will not activate the venv.
# --------------------------------------------------------------------------------
target="/etc/bash.bashrc"
marker="# Activate dwlab environment for interactive shells"

# Check if the marker already exists
if grep -qF "$marker" "$target"; then
    echo "DW-Lab: dwlab environment activation snippet already present in $target"
else
    echo "DW-Lab: Appending dwlab environment activation snippet to $target"
    # Append the snippet

    echo "# Activate dwlab environment for interactive shells" >> "$target"
    echo "echo \"DW-Lab: Activating dwlab environment for interactive shells...\"" >> "$target"
    echo "if [ -r /usr/local/bin/dwlab.sh ]; then" >> "$target"
    echo "    source /usr/local/bin/dwlab.sh" >> "$target"
    echo "fi" >> "$target"

    echo "DW-Lab: Appended dwlab environment activation snippet to $target"
fi
exit 0
