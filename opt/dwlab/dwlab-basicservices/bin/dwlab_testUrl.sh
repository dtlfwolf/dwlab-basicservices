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
#   This script tests the availability of a URL using curl with hhtps/http.
#   Certificate validation is disabled.
#   The script requires the following parameters:
#
# Parameters  :
#  --yamlFile FILE     Path to the YAML file, containing the hostnames and IP addresses.
#  --out-file FILE    Path to the output file, writing the first reachable url into it
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
    echo "  --port PORT         Port number to test (default: <443/80>) "
    echo "  --url_extension     URL extension to test (default: <null>, e.g /cmk_dwlab/checkmk) "
    echo "  -o, --output        Output file (default: <null>, e.g. /tmp/output.txt) "
    echo "  -v, --verbose       Enable verbose mode"
    echo "  -h, --help          Show this help message and exit"
    echo
    echo "Example:"
    echo "  $0 --yamlFile ip_fqdns.yaml --verbose"
}


port=""
url_extension=""
verbose=false
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
        show_help
        exit 0
        ;;
    --yamlFile)
        if [[ -n "$2" && ! "$2" =~ ^- ]]; then
            yamlFile="$2"
            echo "DW-Lab: yamlFile=$yamlFile"
            shift 2
        else
            echo "DW-Lab: --yamlFile requires a file path argument"
            exit 4
        fi
        ;;
    --port)
        if [[ -n "$2" && ! "$2" =~ ^- ]]; then
            port=":"$2
            echo "DW-Lab: port=$port"
            shift 2
        else
            echo "DW-Lab: --port requires a port number argument"
            exit 4
        fi
        ;;
    --url_extension)
        if [[ -n "$2" && ! "$2" =~ ^- ]]; then
            url_extension="$2"
            echo "DW-Lab: url_extension=$url_extension"
            shift 2
        else
            echo "DW-Lab: --url_extension requires a URL extension argument"
            exit 4
        fi
        ;;
    -o|--output-file)
        if [[ -n "$2" && ! "$2" =~ ^- ]]; then
            outputFile="$2"
            echo "DW-Lab: outputFile=$outputFile"
            shift 2
        else
            echo "DW-Lab: -o|--output-file requires a file path argument"
            exit 4
        fi
        ;;
    -v|--verbose)
        verbose=true
        shift
        ;;
    *)  
        echo "Invalid option: $1"
        exit 8
        ;;
  esac
done
if [[ -z "$yamlFile" ]]; then
    echo "DW-Lab: $thisScript: Error: --yamlFile is required"
    exit 8
fi
if [[ -z "$outputFile" ]]; then
    echo "DW-Lab: $thisScript: Error: -o|--output-file is required"
    exit 8
fi
[[ "$verbose" == true ]] && echo "DW-Lab: ************************************************************************************************************"
[[ "$verbose" == true ]] && echo "DW-Lab: $thisScript"
[[ "$verbose" == true ]] && echo "DW-Lab: Parameters already read"

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
[[ "$verbose" == true ]] && echo "DWLab_PackageHome=$DWLab_PackageHome"
#

SOURCE="$DWLab_PackageHome/../."
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

export DWLab_EnvironmentHome=$DIR
[[ "$verbose" == true ]] && echo "DWLab_EnvironmentHome=$DWLab_EnvironmentHome"
#



[[ "$verbose" == true ]] && echo "DW-Lab: Read YAML file, containing runtime settings"
#
# Read YAML file, containing runtime settings
#
source dwlab_bash_yaml.sh
if [ $? != 0 ]
then
  echo 'DW-Lab: *********************************************'
  echo 'DW-Lab: '$thisScript':'
  echo "DW-Lab: Cannot source file dwlab_bash_yaml.sh"
  echo 'DW-Lab: Aborting'
  echo 'DW-Lab: *********************************************'
  exit 8
fi
# create_variables "$DWLab_PackageHome/etc/dw-lab_InstallationSettings.yaml"
create_variables $yamlFile

index=0
url_available=false
reachable_url=null
while true; do
    ip_var="hostsettings__ip[$index]"
    [[ "$verbose" == true ]] && echo "DW-Lab: index="$index
    [[ "$verbose" == true ]] && echo "DW-Lab: ip_var="$ip_var
    fqdns_var="hostsettings__fqdns[$index]"
    [[ "$verbose" == true ]] && echo "DW-Lab: fqdns_var="$fqdns_var

    ip="${!ip_var}"
    [[ "$verbose" == true ]] && echo "DW-Lab: ip="$ip
    [[ "$verbose" == true ]] && echo "DW-Lab: fqdns="${!fqdns_var}

    # Test for end of list
    if [ -z "$ip" ]; then
        break
    fi

    # Collect all candidates: FQDN(s) and IP
    candidates=()

    # Multiple fqdns
    if [ -n "${!fqdns_var}" ]; then
        eval "candidates+=(\"\${${fqdns_var}}\")"
    fi

    # Add raw IP last (fallback)
    candidates+=("$ip")

    # Try each candidate
    reachable_url="null"
    for c in "${candidates[@]}"; do
        for proto in https http; do
            url="$proto://$c$port$url_extension"
            [[ "$verbose" == true ]] && echo "DW-Lab: Testing url="$url
            curl --insecure --connect-timeout 3 -s -o /dev/null "$url"
            if [ $? == 0 ] ; then
                reachable_url="$url"
                [[ "$verbose" == true ]] && echo "DW-Lab: Found reachable url="$reachable_url
                url_available=true
            else
                [[ "$verbose" == true ]] && echo "DW-Lab: url="$url" not reachable"
            fi
            [[ "$url_available" == true ]] && break
        done
        [[ "$url_available" == true ]] && break
    done

    # Output result
    [[ "$verbose" == true ]] && echo "DW-Lab:  - ip: $ip"
    [[ "$verbose" == true ]] && echo "DW-Lab:    reachable_url: \"$reachable_url\""
    [[ "$url_available" == true ]] && break
    ((index++))
done

if [[ "$url_available" == false ]]; then
    echo "DW-Lab: No reachable url found"
    echo "null" > $outputFile
    returncode=4
else
    echo "DW-Lab: Found reachable url: $reachable_url"
    echo "$reachable_url" > $outputFile
    returncode=0
fi
exit $returncode
