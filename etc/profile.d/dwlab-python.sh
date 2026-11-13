# Shared DW-Lab runtime discovery; this does not create or activate a venv.
# Use the installation-owned path, not an inherited environment override.
export DWLAB_PYTHON_VENV=/opt/dwlab/venv

if [ -d "$DWLAB_PYTHON_VENV/bin" ]; then
  case ":${PATH-}:" in
    *":$DWLAB_PYTHON_VENV/bin:"*) ;;
    *)
      PATH="$DWLAB_PYTHON_VENV/bin${PATH:+:$PATH}"
      export PATH
      ;;
  esac
fi
