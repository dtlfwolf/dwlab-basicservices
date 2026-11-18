"""Standalone transfer tests without SSH access or privileged source reads."""

import importlib.util
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "opt/dwlab/dwlab-basicservices/lib/dwlab_scp.py"
spec = importlib.util.spec_from_file_location("dwlab_scp", MODULE)
transfer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = transfer
spec.loader.exec_module(transfer)


class TestSecureTransfer:
    def runner(self, calls, payload=b"private credential fixture", source_error=False):
        def run(command, **kwargs):
            calls.append((command, kwargs))
            assert command[:5] == ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15"]
            assert "StrictHostKeyChecking=no" not in command
            if shlex.split(command[-1])[:4] == ["sudo", "-n", "cat", "--"]:
                kwargs["stdout"].write(payload)
                assert os.stat(kwargs["stdout"].name).st_mode & 0o777 == 0o600
                if source_error:
                    raise subprocess.CalledProcessError(1, command, stderr=b"read denied")
                return subprocess.CompletedProcess(command, 0)
            # Exercise the exact receiving shell on a disposable local directory.
            return subprocess.run(["/bin/sh", "-c", command[-1]], **kwargs)
        return run

    @pytest.mark.parametrize("remote", [False, True])
    def test_copy_and_cleanup(self, tmp_path, monkeypatch, remote):
        staging = tmp_path / "staging"
        staging.mkdir()
        monkeypatch.setattr(transfer.tempfile, "tempdir", str(staging))
        destination = tmp_path / "destination with 'quotes'"
        destination.mkdir()
        calls = []
        name = "client 'quoted';$(false).deb"
        address = f"user@target:{destination}" if remote else str(destination)
        transfer.SecureTransfer(self.runner(calls)).copy(
            f"user@source:/protected/{name}", address
        )
        output = destination / name
        assert output.read_bytes() == b"private credential fixture"
        assert output.stat().st_mode & 0o777 == 0o600
        assert shlex.split(calls[0][0][-1])[-1] == f"/protected/{name}"
        assert list(staging.iterdir()) == []
        assert list(destination.iterdir()) == [output]

    @pytest.mark.parametrize("remote", [False, True])
    def test_existing_symlink_is_replaced_not_followed(self, tmp_path, remote):
        protected = tmp_path / "protected"
        protected.write_text("unchanged")
        destination = tmp_path / "destination"
        destination.mkdir()
        (destination / "client.deb").symlink_to(protected)
        address = f"user@target:{destination}" if remote else str(destination)
        transfer.SecureTransfer(self.runner([])).copy(
            "user@source:/protected/client.deb", address
        )
        assert protected.read_text() == "unchanged"
        assert not (destination / "client.deb").is_symlink()
        assert (destination / "client.deb").stat().st_mode & 0o777 == 0o600

    def test_failed_source_never_publishes_partial_bytes(self, tmp_path, monkeypatch):
        staging = tmp_path / "staging"
        staging.mkdir()
        monkeypatch.setattr(transfer.tempfile, "tempdir", str(staging))
        destination = tmp_path / "client.deb"
        destination.write_text("existing")
        calls = []
        with pytest.raises(transfer.TransferError, match="read denied"):
            transfer.SecureTransfer(self.runner(calls, source_error=True)).copy(
                "user@source:/protected/client.deb", str(tmp_path)
            )
        assert destination.read_text() == "existing"
        assert len(calls) == 1
        assert list(staging.iterdir()) == []

    @pytest.mark.parametrize("remote", [False, True])
    def test_missing_destination_is_reported(self, tmp_path, remote):
        directory = tmp_path / "missing"
        destination = f"user@target:{directory}" if remote else str(directory)
        with pytest.raises(transfer.TransferError, match="directory does not exist"):
            transfer.SecureTransfer(self.runner([])).copy(
                "user@source:/protected/client.deb", destination
            )
        assert not directory.exists()

    @pytest.mark.parametrize("source", [
        "-option:/file", "host:relative", "host:/file\nmalicious",
        "host:/packages/*.deb", "host:/directory/", "host:/directory/..",
    ])
    def test_invalid_source_fails_before_ssh(self, tmp_path, source):
        calls = []
        with pytest.raises(transfer.TransferError):
            transfer.SecureTransfer(self.runner(calls)).copy(source, str(tmp_path))
        assert not calls

    def test_destination_write_failure_removes_remote_temporary(self, tmp_path):
        (tmp_path / "client.deb").mkdir()
        with pytest.raises(transfer.TransferError):
            transfer.SecureTransfer(self.runner([])).copy(
                "user@source:/protected/client.deb", f"user@target:{tmp_path}"
            )
        assert list(tmp_path.iterdir()) == [tmp_path / "client.deb"]

    def test_short_remote_upload_preserves_existing_destination(self, tmp_path):
        existing = tmp_path / "client.deb"
        existing.write_text("existing package")
        normal_runner = self.runner([])

        def truncate_upload(command, **kwargs):
            if shlex.split(command[-1])[0] == "sh":
                with tempfile.TemporaryFile() as short_input:
                    short_input.write(b"truncated")
                    short_input.seek(0)
                    kwargs["stdin"] = short_input
                    return normal_runner(command, **kwargs)
            return normal_runner(command, **kwargs)

        with pytest.raises(transfer.TransferError, match="checksum mismatch"):
            transfer.SecureTransfer(truncate_upload).copy(
                "user@source:/protected/client.deb", f"user@target:{tmp_path}"
            )
        assert existing.read_text() == "existing package"
        assert list(tmp_path.iterdir()) == [existing]

    def test_shell_entrypoint_has_readable_error(self):
        script = ROOT / "opt/dwlab/dwlab-basicservices/bin/dwlab-scp.sh"
        result = subprocess.run(
            ["bash", str(script), "invalid", "/tmp"],
            text=True, capture_output=True,
        )
        assert result.returncode == 1
        assert "Transfer failed:" in result.stderr
        assert "Traceback" not in result.stderr

    def test_shell_entrypoint_help(self):
        script = ROOT / "opt/dwlab/dwlab-basicservices/bin/dwlab-scp.sh"
        result = subprocess.run(
            ["bash", str(script), "--help"], text=True, capture_output=True,
        )
        assert result.returncode == 0
        assert "source" in result.stdout
