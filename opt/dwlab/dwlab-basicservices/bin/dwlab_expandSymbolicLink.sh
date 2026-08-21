#
#- Copyright:
#
# Company    = "DW-Lab GmbH"
# Department = "basicServices"
# Creation   = "18-Oct-2025"
# Version    = "1.0"
# Author     = "Detlef Wolf"
#
# Usage:  source dwlab_expandSymbolicLink.sh
#
# Description:
#   Expand a symbolic link to its target directory path
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
# 18-Oct-2025  D. Wolf       - Creation
#


dwlab_expandSymbolicLink() {
    local SOURCE="$1"
    while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
      local DIR="$( cd -P "$( dirname "$SOURCE" )" 2>/dev/null && pwd )"
      SOURCE="$(readlink "$SOURCE" 2>/dev/null)"
      [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
    done
    local DIR="$( cd -P "$( dirname "$SOURCE" )" 2>/dev/null && pwd )"
    echo "$DIR"
}
