"""Standalone transfer tests without SSH access or privileged source reads."""

import importlib.util
import io
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
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


class TestRecursiveTransfer:
    def archive(self, extra=None):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as archive:
            root = tarfile.TarInfo("tree")
            root.type = tarfile.DIRTYPE
            archive.addfile(root)
            script = tarfile.TarInfo("tree/run.sh")
            script.mode = 0o4755
            content = b"#!/bin/sh\nexit 0\n"
            script.size = len(content)
            archive.addfile(script, io.BytesIO(content))
            nested = tarfile.TarInfo("tree/nested/settings")
            nested.size = 6
            archive.addfile(nested, io.BytesIO(b"secret"))
            empty = tarfile.TarInfo("tree/empty")
            empty.type = tarfile.DIRTYPE
            archive.addfile(empty)
            if extra is not None:
                archive.addfile(extra, io.BytesIO(b""))
        return buffer.getvalue()

    def runner(self, payload, calls, truncate=False):
        def run(command, **kwargs):
            calls.append(command)
            remote_command = shlex.split(command[-1])
            if remote_command[:3] == ["sudo", "-n", "tar"]:
                kwargs["stdout"].write(payload)
                return subprocess.CompletedProcess(command, 0)
            assert remote_command[0] == "python3"
            remote_command[0] = sys.executable
            if truncate:
                with tempfile.TemporaryFile() as short_input:
                    short_input.write(payload[:512])
                    short_input.seek(0)
                    kwargs["stdin"] = short_input
                    return subprocess.run(remote_command, **kwargs)
            return subprocess.run(remote_command, **kwargs)
        return run

    @pytest.mark.parametrize("remote", [False, True])
    def test_recursive_copy_is_private_and_preserves_owner_execute(self, tmp_path, remote):
        destination = f"target:{tmp_path}" if remote else str(tmp_path)
        calls = []
        transfer.SecureTransfer(self.runner(self.archive(), calls), jump="user@jump:2222").copy(
            "source:/protected/tree/", destination, recursive=True
        )
        root = tmp_path / "tree"
        assert (root / "nested/settings").read_text() == "secret"
        assert (root / "run.sh").stat().st_mode & 0o7777 == 0o700
        assert (root / "nested/settings").stat().st_mode & 0o7777 == 0o600
        for directory in (root, root / "nested", root / "empty"):
            assert directory.stat().st_mode & 0o7777 == 0o700
        assert list(tmp_path.iterdir()) == [root]
        for command in calls:
            assert command[5:7] == ["-J", "user@jump:2222"]
            assert "StrictHostKeyChecking=no" not in command
        assert shlex.split(calls[0][-1]) == [
            "sudo", "-n", "tar", "--format=pax", "-C", "/protected", "-cf", "-", "--", "tree"
        ]

    @pytest.mark.parametrize("remote", [False, True])
    def test_existing_tree_is_not_merged(self, tmp_path, remote):
        root = tmp_path / "tree"
        root.mkdir()
        (root / "keep").write_text("unchanged")
        destination = f"target:{tmp_path}" if remote else str(tmp_path)
        with pytest.raises(transfer.TransferError, match="already exists"):
            transfer.SecureTransfer(self.runner(self.archive(), [])).copy(
                "source:/protected/tree", destination, recursive=True
            )
        assert list(root.iterdir()) == [root / "keep"]
        assert (root / "keep").read_text() == "unchanged"

    @pytest.mark.parametrize("name,kind", [
        ("tree/link", tarfile.SYMTYPE),
        ("tree/hardlink", tarfile.LNKTYPE),
        ("tree/fifo", tarfile.FIFOTYPE),
        ("tree/device", tarfile.CHRTYPE),
        ("tree/../escape", tarfile.REGTYPE),
        ("/absolute", tarfile.REGTYPE),
        ("another-root", tarfile.REGTYPE),
        ("tree/run.sh", tarfile.REGTYPE),
    ])
    def test_unsafe_archive_is_rejected_before_destination_connection(self, tmp_path, name, kind):
        entry = tarfile.TarInfo(name)
        entry.type = kind
        entry.linkname = "/outside"
        calls = []
        with pytest.raises(transfer.TransferError, match="Unsafe archive"):
            transfer.SecureTransfer(self.runner(self.archive(entry), calls)).copy(
                "source:/protected/tree", f"target:{tmp_path}", recursive=True
            )
        assert len(calls) == 1
        assert list(tmp_path.iterdir()) == []

    def test_truncated_upload_never_publishes_tree(self, tmp_path):
        with pytest.raises(transfer.TransferError, match="checksum mismatch"):
            transfer.SecureTransfer(self.runner(self.archive(), [], truncate=True)).copy(
                "source:/protected/tree", f"target:{tmp_path}", recursive=True
            )
        assert list(tmp_path.iterdir()) == []

    def test_jump_overrides(self, tmp_path):
        calls = []
        transfer.SecureTransfer(
            self.runner(self.archive(), calls), jump="common-jump",
            source_jump="none", destination_jump="user@hop1,user@hop2:2222",
        ).copy("source:/protected/tree", f"target:{tmp_path}", recursive=True)
        assert "-J" not in calls[0]
        assert calls[1][5:7] == ["-J", "user@hop1,user@hop2:2222"]

    @pytest.mark.parametrize("jump", ["-option", "host;false", "user@host,", "host\n", ""])
    def test_invalid_jump_is_rejected(self, jump):
        with pytest.raises(transfer.TransferError, match="Invalid jump"):
            transfer.SecureTransfer(jump=jump)

    def test_cli_passes_options_to_transfer(self, monkeypatch):
        calls = []

        class FakeTransfer:
            def __init__(self, **options):
                calls.append(options)

            def copy(self, source, destination, **options):
                calls.append((source, destination, options))

        monkeypatch.setattr(transfer, "SecureTransfer", FakeTransfer)
        assert transfer.TransferCli().run([
            "-r", "-J", "jump", "--source-jump", "none",
            "--destination-jump", "other", "source:/tree", "target:/tmp",
        ]) == 0
        assert calls == [
            {"jump": "jump", "source_jump": "none", "destination_jump": "other"},
            ("source:/tree", "target:/tmp", {"recursive": True}),
        ]

    @pytest.mark.parametrize("limit", ["MAX_MEMBERS", "MAX_BYTES"])
    def test_archive_limits_are_enforced(self, tmp_path, monkeypatch, limit):
        monkeypatch.setattr(transfer.TreeArchive, limit, 1)
        with pytest.raises(transfer.TransferError, match="limit"):
            transfer.SecureTransfer(self.runner(self.archive(), [])).copy(
                "source:/protected/tree", str(tmp_path), recursive=True
            )
        assert list(tmp_path.iterdir()) == []

    def test_real_gnu_tar_source_and_remote_receiver(self, tmp_path):
        source = tmp_path / "source 'quoted'"
        source.mkdir()
        (source / ".hidden").write_text("private")
        (source / "empty").mkdir()
        destination = tmp_path / "destination"
        destination.mkdir()

        def run(command, **kwargs):
            arguments = shlex.split(command[-1])
            if arguments[:3] == ["sudo", "-n", "tar"]:
                arguments = arguments[2:]
            else:
                assert arguments[0] == "python3"
                arguments[0] = sys.executable
            return subprocess.run(arguments, **kwargs)

        transfer.SecureTransfer(run).copy(
            f"source:{source}", f"target:{destination}", recursive=True
        )
        assert (destination / source.name / ".hidden").read_text() == "private"
        assert (destination / source.name / "empty").is_dir()

    def test_single_file_jump_is_forwarded_to_both_endpoints(self, tmp_path):
        calls = []
        transfer.SecureTransfer(
            TestSecureTransfer().runner(calls), jump="user@jump"
        ).copy("source:/protected/client.deb", f"target:{tmp_path}")
        assert len(calls) == 2
        for command, _ in calls:
            assert command[5:7] == ["-J", "user@jump"]
