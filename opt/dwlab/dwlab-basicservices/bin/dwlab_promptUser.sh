#!/bin/bash

# Function to prompt the user for input.
prompt_user() {
  if [ ! -t 0 ] || [ ! -t 1 ]; then
    echo "DW-Lab: No interactive terminal available for confirmation." >&2
    return 1
  fi

  echo "DW-Lab: Interactive terminal detected: $(tty)"
  while true; do
    read -r -p "DW-Lab: Do you want to continue? Enter 'yes' to continue or 'no' to exit: " answer
    case "$answer" in
      yes)
        return 0
        ;;
      no)
        return 1
        ;;
      *)
        echo "DW-Lab: Please answer yes or no."
        ;;
    esac
  done
}
