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



git config --global user.email "info@dw-lab.de"
if [ $? != 0 ]
then
  echo "DW-Lab: $thisScript:"
  echo "DW-Lab: Error during git config user.email"
  exit 8
fi
git config --global user.name "dwlab-info"
if [ $? != 0 ]
then
  echo "DW-Lab: $thisScript:"
  echo "DW-Lab: Error during git config user.name"
  exit 8
fi
git config --global credential.helper store
if [ $? != 0 ]
then
  echo "DW-Lab: $thisScript:"
  echo "DW-Lab: Error during git config credential.helper"
  exit 8
fi

python3 -m venv /opt/dwlab/venv
if [ $? != 0 ]
then
  echo "DW-Lab: $thisScript:"
  echo "DW-Lab: Error during creation of python3 venv"
  exit 8
fi
source /opt/dwlab/venv/bin/activate
if [ $? != 0 ]
then
  echo "DW-Lab: $thisScript:"
  echo "DW-Lab: Error during activation of python3 venv"
  exit 8
fi

pip install --upgrade pip
if [ $? != 0 ]
then
  echo "DW-Lab: $thisScript:"
  echo "DW-Lab: Error during upgrade of pip"
  exit 8
fi

pip install --upgrade setuptools
if [ $? != 0 ]
then
  echo "DW-Lab: $thisScript:"
  echo "DW-Lab: Error during upgrade of setuptools"
  exit 8
fi

pip install --upgrade wheel
if [ $? != 0 ]
then
  echo "DW-Lab: $thisScript:"
  echo "DW-Lab: Error during upgrade of wheel"
  exit 8
fi

pip install --upgrade git+https://github.com/dtlfwolf/dwlab-basicpy.git
if [ $? != 0 ]
then
  echo "DW-Lab: $thisScript:"
  echo "DW-Lab: Error during installation of dwlab-basicpy"
  exit 8
fi

chmod 755 /opt/dwlab/venv


# -------------------------------------------------------------------------------
# Append activation dwlab venv in /etc/bash.bashrc for interactive shells
# This is needed to ensure that the dwlab venv is activated in interactive shells
# This is a workaround for the fact that /etc/profile.d/dwlab-basicservices.sh
# is not sourced in interactive shells by default.
# This script should be run as root to modify /etc/bash.bashrc
# It appends a snippet to /etc/bash.bashrc that activates the dwlab venv
# when an interactive shell is started.
# The snippet checks if /etc/profile.d/dwlab.sh exists and sources it.
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
    echo "if [ -r /etc/profile.d/dwlab.sh ]; then" >> "$target"
    echo "    source /etc/profile.d/dwlab.sh" >> "$target"
    echo "fi" >> "$target"

    echo "DW-Lab: Appended dwlab environment activation snippet to $target"
fi
exit 0
