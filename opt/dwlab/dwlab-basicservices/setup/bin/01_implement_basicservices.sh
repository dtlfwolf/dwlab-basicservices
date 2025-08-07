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
# Usage:  installation/bin/01_implement_basicservices.sh
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
# 03-Nov-2024  D. Wolf       - Creation

thisScript=$0

echo 'DW-Lab: ************************************************************************************************************'
echo 'DW-Lab: '$thisScript


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
echo "DW-Lab: DWLab_CONTROL_HOME=$DWLab_CONTROL_HOME"

SOURCE="$DWLab_CONTROL_HOME/../."
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

export DWLab_PackageHome=$DIR
echo "DWLab_PackageHome=$DWLab_PackageHome"
#

SOURCE="$DWLab_PackageHome/../."
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

export DWLab_EnvironmentHome=$DIR
echo "DWLab_EnvironmentHome=$DWLab_EnvironmentHome"
#

environment=$(basename $DWLab_EnvironmentHome)
source "/opt/dwlab/$environment/bin/dwlab_bash_yaml.sh"
if [ $? != 0 ]
then
  echo "DW-Lab: $thisScript:"
  echo "DW-Lab: Cannot source file /opt/dwlab/$environment/bin/dwlab_bash_yaml.sh"
  exit 8
fi
create_variables "/opt/dwlab/$environment/etc/dw-lab_InstallationSettings.yaml"


chmod 755 /opt/dwlab
find $DWLab_PackageHome -type f -exec chmod 755 {} \;

find $DWLab_PackageHome -type f -name '*.sh' -exec chmod +x {} \;
find $DWLab_PackageHome -type f -name '*.py' -exec chmod +x {} \;

chmod 755 /etc/profile.d/dwlab-basicservices.sh

# Source the python venv bash profile to make the changes effective
if [ -f /opt/dwlab/venv/bin/activate ]; then
  source /opt/dwlab/venv/bin/activate
else
  echo "DW-Lab: $thisScript:"
  echo "DW-Lab: /opt/dwlab/venv/bin/activate not found, cannot source it."
  exit 1
fi
exit 0

