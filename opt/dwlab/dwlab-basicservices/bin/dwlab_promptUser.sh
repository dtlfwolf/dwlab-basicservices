# Function to prompt the user for input
prompt_user() {
  if tty | grep -q 'not a tty'
  then
    echo "DW-Lab: You are connected via SSH or similiar in a pseudo terminal. No confirmation is required."
    return 0
  else
    echo "DW-Lab: You are connected via a terminal with tty output: `tty`."
    while true; do
      read -p "DW-Lab: Do you want to continue? Enter 'yes' to continue or 'no' to exit: " answer
      case $answer in
        "yes" )
          return 0;;  # Return success status (0) for "yes"
        "no" )
          return 1;;  # Return failure status (1) for "no"
        * )
          echo "DW-Lab: Please answer yes or no.";;
      esac
    done
  fi
}
