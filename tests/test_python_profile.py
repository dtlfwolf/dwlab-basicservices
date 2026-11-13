"""The shared Python shell environment is delivered, not inferred from login state."""

import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "etc/profile.d/dwlab-python.sh"


class TestPythonProfile:
    def run_profile(self, tmp_path, path="/usr/bin:/bin", installed=True, shell="/bin/sh"):
        venv = tmp_path / "venv"
        if installed:
            (venv / "bin").mkdir(parents=True)
        # Substitute the fixed installation path only in this disposable shell
        # input, never on the host or in the package under test.
        snippet = PROFILE.read_text().replace("/opt/dwlab/venv", str(venv))
        result = subprocess.run(
            [shell, "-eu", "-c", snippet + "\n" + snippet +
             '\nprintf "%s\\n" "$DWLAB_PYTHON_VENV" "$PATH" "${VIRTUAL_ENV-unset}"'],
            env={**os.environ, "PATH": path, "DWLAB_PYTHON_VENV": "/untrusted/runtime"},
            capture_output=True, text=True, check=True)
        return venv, result.stdout.splitlines()

    @pytest.mark.parametrize("shell", ["/bin/sh", "/bin/bash"])
    def test_existing_runtime_is_added_once(self, tmp_path, shell):
        venv, lines = self.run_profile(tmp_path, shell=shell)
        assert lines[0] == str(venv)
        assert lines[1] == f"{venv}/bin:/usr/bin:/bin"
        assert lines[2] == os.environ.get("VIRTUAL_ENV", "unset")

    def test_absent_runtime_does_not_break_login_or_add_a_dead_path(self, tmp_path):
        _, lines = self.run_profile(tmp_path, installed=False)
        assert lines[1] == "/usr/bin:/bin"

    def test_empty_path_is_safe(self, tmp_path):
        venv, lines = self.run_profile(tmp_path, path="")
        assert lines[1] == f"{venv}/bin"

    def test_archive_delivers_the_profile_as_a_conffile(self, tmp_path):
        # Build from this package's payload only, independently of sibling repos
        # or the shared development builder.
        import shutil

        stage = tmp_path / "stage"
        for name in ("DEBIAN", "etc", "opt", "usr"):
            shutil.copytree(ROOT / name, stage / name)
        # The standard binary builder normalizes maintainer-script modes.
        for name in ("postinst", "postrm"):
            (stage / "DEBIAN" / name).chmod(0o755)
        archive = tmp_path / "basicservices.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(stage), str(archive)],
                       check=True, capture_output=True)
        payload, metadata = tmp_path / "payload", tmp_path / "metadata"
        subprocess.run(["dpkg-deb", "-x", str(archive), str(payload)], check=True)
        subprocess.run(["dpkg-deb", "-e", str(archive), str(metadata)], check=True)
        assert (payload / "etc/profile.d/dwlab-python.sh").read_bytes() == PROFILE.read_bytes()
        assert "/etc/profile.d/dwlab-python.sh" in (metadata / "conffiles").read_text().splitlines()
