# Function to check if OpenVPN is installed using dpkg (Debian-based)
check_dpkg() {
  packageName=$1
  if dpkg -l | awk '$2 == "bind9" && $1 ~ /^ii/' | grep -q "$packageName"
  then
    echo "DW-Lab: $packageName package is already installed."
    return 0
  else
    echo "DW-Lab: $packageName package is not installed yet."
    return 4
  fi
}

# Function to check if OpenVPN is installed using rpm (RPM-based)
check_rpm() {
  packageName=$1
  if rpm -q $packageName >/dev/null 2>&1
  then
    echo "DW-Lab:  $packageName package is already installed."
    return 0
  else
    echo "DW-Lab: $packageName package is not installed yet."
    return 4
  fi
}

dwlab_installOSPackage() {
  packageName=$1  
  # Check which package manager is available
  if command -v dpkg >/dev/null 2>&1; then
    check_dpkg $packageName
    if [ $? != "0" ]
    then
      echo "DW-Lab: Installing $packageName package now."
      apt install -y $packageName
    fi
  elif command -v rpm >/dev/null 2>&1; then
    check_rpm $packageName
    if [ $? != "0" ]
    then
      echo "DW-Lab: Installing $packageName package now."
      yum install -y $packageName
    fi
  else
    echo "Cannot determine package manager. $packageName package check failed."
  fi
}

