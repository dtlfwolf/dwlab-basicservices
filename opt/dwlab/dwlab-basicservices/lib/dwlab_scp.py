"""Privileged remote file reads with private staging and atomic publication."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import logging
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import tempfile
from typing import Callable


class TransferError(Exception):
    """A transfer could not be completed safely."""


@dataclass(frozen=True)
class RemoteLocation:
    """An SSH target and an absolute, literal path on that target."""

    host: str
    path: str

    @classmethod
    def parse(cls, value: str) -> RemoteLocation:
        """Parse USER@HOST:/path without shell expansion or SSH options."""
        host, separator, path = value.partition(":")
        if (
            not separator
            or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.@-]*", host)
            or path.startswith("//")
            or not path.startswith("/")
            or any(ord(char) < 32 or ord(char) == 127 for char in value)
        ):
            raise TransferError("Use an SSH host or alias followed by :/absolute/path.")
        return cls(host, path)


class SecureTransfer:
    """Read with source sudo; publish as the destination login identity."""

    _PUBLISH_SCRIPT = """set -eu
umask 077
directory=$1
filename=$2
checksum=$3
test -d "$directory" || { echo 'Destination directory does not exist' >&2; exit 1; }
temporary=$(mktemp -- "$directory/.dwlab-scp.XXXXXXXXXX")
trap 'rm -f -- "$temporary"' EXIT
trap 'exit 1' HUP INT TERM
cat > "$temporary"
actual=$(sha256sum -- "$temporary")
test "${actual%% *}" = "$checksum" || { echo 'Transfer checksum mismatch' >&2; exit 1; }
chmod 600 -- "$temporary"
mv -fT -- "$temporary" "$directory/$filename"
"""

    def __init__(self, runner: Callable = subprocess.run):
        self._runner = runner

    def copy(self, source: str, destination: str) -> None:
        """Copy one exact remote file into an existing destination directory."""
        origin = RemoteLocation.parse(source)
        if any(char in origin.path for char in "*?[]"):
            raise TransferError("Specify one exact source filename; wildcards are not supported.")
        name = PurePosixPath(origin.path).name
        if origin.path.endswith("/") or name in {"", ".", ".."}:
            raise TransferError("The source must name a file, not a directory.")
        target = RemoteLocation.parse(destination) if ":" in destination else None
        with tempfile.TemporaryDirectory(prefix="dwlab-scp-") as staging:
            staged_file = Path(staging) / "payload"
            descriptor = os.open(staged_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as output:
                self._ssh(
                    origin.host,
                    shlex.join(["sudo", "-n", "cat", "--", origin.path]),
                    stdin=subprocess.DEVNULL, stdout=output,
                )
            if target:
                command = shlex.join([
                    "sh", "-c", self._PUBLISH_SCRIPT, "dwlab-scp",
                    target.path, name, self._digest(staged_file),
                ])
                with staged_file.open("rb") as input_file:
                    self._ssh(target.host, command, stdin=input_file,
                              stdout=subprocess.DEVNULL)
            else:
                self._publish_local(staged_file, Path(destination), name)

    def _digest(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _ssh(self, host: str, command: str, **streams) -> None:
        try:
            self._runner(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
                 "--", host, command],
                check=True, stderr=subprocess.PIPE, **streams,
            )
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or b"").decode(errors="replace").strip()
            raise TransferError(
                f"SSH transfer on {host} failed (exit {exc.returncode})"
                + (f": {detail}" if detail else ".")
            ) from exc

    def _publish_local(self, source: Path, directory: Path, name: str) -> None:
        if not directory.is_dir():
            raise TransferError("Destination directory does not exist.")
        descriptor, temporary = tempfile.mkstemp(prefix=".dwlab-scp-", dir=directory)
        try:
            with os.fdopen(descriptor, "wb") as output, source.open("rb") as input_file:
                shutil.copyfileobj(input_file, output)
            os.replace(temporary, directory / name)
        finally:
            Path(temporary).unlink(missing_ok=True)


class TransferCli:
    """Console adapter for secure transfer; no global logging configuration."""

    def run(self, argv: list[str] | None = None) -> int:
        """Return zero only after successful publication of the complete file."""
        parser = argparse.ArgumentParser(
            prog="dwlab-scp.sh",
            description="Copy one remote file using source sudo into a destination directory.",
        )
        parser.add_argument("source", help="USER@HOST:/absolute/file (no wildcards)")
        parser.add_argument("destination", help="Local directory or USER@HOST:/directory")
        args = parser.parse_args(argv)
        logger = logging.Logger("dwlab-scp")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("dwlab-scp.sh: %(message)s"))
        logger.addHandler(handler)
        try:
            logger.info("Transfer started.")
            SecureTransfer().copy(args.source, args.destination)
        except (TransferError, OSError) as exc:
            logger.error("Transfer failed: %s", exc)
            return 1
        except KeyboardInterrupt:
            logger.error("Transfer interrupted.")
            return 130
        logger.info("Transfer completed successfully (destination mode 0600).")
        return 0


if __name__ == "__main__":
    raise SystemExit(TransferCli().run())
