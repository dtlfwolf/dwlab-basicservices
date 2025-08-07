#!/bin/bash
#
#- Copyright:
#
# Company    = "DW-Lab GmbH"
# Department = "checkmk"
# Creation   = "23-May-2025"
# Version    = "1.0"
# Author     = "Detlef Wolf"
#
# Usage:  /opt/dwlab/dwlab-basicservices/bin/dwlab_writeNetworkSettingsYaml.sh
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
# 23-May-2025  D. Wolf       - Creation

thisScript=$0


# ----------------------------------------
# Help Function
# ----------------------------------------
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --yamlFile FILE     Path to the YAML file"
    echo "  -v, --verbose       Enable verbose mode"
    echo "  -h, --help          Show this help message and exit"
    echo
    echo "Example:"
    echo "  $0 --yamlFile ip_fqdns.yaml --verbose"
}



# ----------------------------------------
# Default Values
# ----------------------------------------
verbose=false
yamlFile=""

# ----------------------------------------
# Argument Parsing Loop
# ----------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      show_help
      exit 0
      ;;
    -v|--verbose)
      verbose=true
      shift
      ;;
    --yamlFile)
      if [[ -n "$2" && ! "$2" =~ ^- ]]; then
          yamlFile="$2"
          shift 2
      else
          echo "Error: --yamlFile requires a file path argument"
          exit 8
      fi
      ;;
    *)
      echo "Unrecognized option or positional argument: $1"
      exit 1
      ;;
  esac
done

# ----------------------------------------
# Validation
# ----------------------------------------
if [[ -z "$yamlFile" ]]; then
  echo "DW-Lab: Error: --yamlFile is required"
  show_help
  exit 1
fi

# ----------------------------------------
# Debug Output if Verbose
# ----------------------------------------
if $verbose; then
  echo "DW-Lab: YAML file: $yaml_file"
  echo "DW-Lab: Verbose mode: ON"
  echo "DW-Lab: ************************************************************************************************************"
  echo "DW-Lab: $thisScript"
  echo "DW-Lab: Parameters already read"
fi



if $verbose; then
    echo "DW-Lab: Setting ennvironment variables"
fi
###############################################################################################################################
## Find out the directory path of the running script
## We expect the Images directory in relative path ./../../Images from the executed script
###############################################################################################################################
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

export DWLab_CONTROL_HOME=$DIR
[[ "$verbose" == true ]] && echo "DW-Lab: DWLab_CONTROL_HOME=$DWLab_CONTROL_HOME"


SOURCE="$DWLab_CONTROL_HOME/../."
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

export DWLab_PackageHome=$DIR
[[ "$verbose" == true ]] && echo "DW-Lab: DWLab_PackageHome=$DWLab_PackageHome"
#

SOURCE="$DWLab_PackageHome/../."
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

export DWLab_EnvironmentHome=$DIR
[[ "$verbose" == true ]] && echo "DW-Lab: DWLab_EnvironmentHome=$DWLab_EnvironmentHome"



# Start YAML structure
echo "# "$yamlFile > "$yamlFile"
echo "# This file shows all IP addresses and their corresponding hostnames" >> "$yamlFile"
echo "# The file has been generated after the cmkcentralclient was installed" >> "$yamlFile"
echo "# To recreate this file run the following command:" >> "$yamlFile"
echo "# "$thisScript >> "$yamlFile"

echo "hostsettings:" > "$yamlFile"

# Loop through all IPs returned by hostname -I
for ip in $(hostname -I); do
    [[ "$verbose" == true ]] && echo "DW-Lab: Processing IP: $ip"
    # Get all PTR hostnames using dig (more reliable than host)
    ptrs=$(dig -x "$ip" +short | sed 's/\.$//' | sort -u)

    # Check if we found any PTR records
    if [ -n "$ptrs" ]; then
        # Found FQDNs
        echo "  - ip: $ip" >> "$yamlFile"
        echo "    fqdns:" >> "$yamlFile"
        echo "$ptrs" | while read -r hostname; do
            echo "      - \"$hostname\"" >> "$yamlFile"
        done
    else
        # No FQDNs found
        echo "  - ip: $ip" >> "$yamlFile"
        echo "    fqdn: null" >> "$yamlFile"
    fi
done

