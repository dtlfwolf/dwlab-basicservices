#!/bin/bash
#
#- Copyright:
#
# Company    = "DW-Lab GmbH"
# Department = "basicServices"
# Creation   = "30-Oct-2024"
# Version    = "1.0"
# Author     = "Detlef Wolf"
#
# Usage:  bin/dwlab_idInfo.sh --help | [--id <userName>] [--format [default]|yaml]
#     This script provides the id info in the requested format
#
# Description:
#
# Parameters  :
#   --id userName   optional    userName info will be shown
#                               if no userName is provided the current user will be used
#   --format        optional    if no format is defined, the default id call will be used
#                               yaml : print yaml to stdout
#   --help          optional    print help information, all other parameters will be ignored
#
#  returnCode:
#   0   successfully executed
#   1   help printed
#   4   userName not found
#   8   error with error messages in stdout
#
# References  :
#       Name      Type      Short description
#      ------------------------------------------------------------
#       id        OS        Print information about USER or the current user
#
# Changes :
# 30-Oct-2024  D. Wolf       - Creation
#
thisScript=$0

# Setting default vaules
userName=""
help=""
format="default"

# Parameter handling
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --id) 
      userName="$2"
      shift
      ;;
    --format) 
      format="$2"
      shift
      ;;
    --help) 
      echo "DW-Lab: Usage for $thisScript"
      echo "DW-Lab: bin/dwlab_idInfo.sh --help | [--id <userName>] [--format [default]|yaml]"
      echo "DW-Lab: This script provides the id info in the requested format"
      exit 1
      ;;
    *)  
      echo "DW-Lab: Unknown option: $1" >&2
      exit 8
      ;;
  esac
  shift
done

 
# Getting id info for the requested user (default: current user) in seperated sections
userId=$(id -u $userName)
if [ $? != 0 ]
then
  # userName not found
  exit 4
fi
groupId=$(id -g $userName)
groupName=$(id -gn $userName)
IFS=' ' read -r -a groups <<< "$(id -G $userName)"
case $format in
  "yaml") 
    # Konvertiert die Ausgabe in YAML-Format
    echo "user:"
    echo "  name: $userName"
    echo "  id: $userId"
    echo "group:"
    echo "  name: $groupName"
    echo "  id: $groupId"
    echo "groups:"
    for i in ${!groups[@]}
    do
      groupId=${groups[${i}]}
      groupName=$(getent group "$groupId" | cut -d: -f1)
      echo "  - name: $groupName"
      echo "    id: $groupId"
    done
    ;;
  "default") 
    id $userName
    ;;
  *)  
    echo "DW-Lab: Unknown format option: $format" >&2
    exit 8
    ;;
esac

exit 0