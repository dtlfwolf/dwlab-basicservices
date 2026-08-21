#!/usr/bin/env bash
#
#- Copyright:
#
# Company    = "DW-Lab GmbH"
# Department = "basicServices"
# Creation   = "06-Oct-2025"
# Version    = "1.0"
# Author     = "Detlef Wolf"
#
# Usage:  bin/dwlab_ensureLogDirectory.sh
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
# 06-Oct-2025  D. Wolf       - Creation
#

if [ ! -d /var/log/dwlab ] 
then
    mkdir -p /var/log/dwlab
fi
chmod 770 /var/log/dwlab


