"""Privileged remote file reads with private staging and atomic publication."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import fnmatch
import hashlib
import inspect
import logging
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
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


class TreeArchive:
    """Validate and publish a regular-file/directory tree without tar extraction."""

    MAX_MEMBERS = 100000
    MAX_BYTES = 100 * 1024 ** 3

    def digest(self, path: Path) -> str:
        """Return a streaming SHA-256 digest."""
        result = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                result.update(chunk)
        return result.hexdigest()

    def validate(self, path: Path, name: str) -> list[tarfile.TarInfo]:
        """Reject traversal, links, special files and excessive logical size."""
        seen = set()
        members = []
        total = 0
        try:
            with tarfile.open(path, "r:") as archive:
                for member in archive:
                    parts = PurePosixPath(member.name).parts
                    if (
                        not parts or parts[0] != name or ".." in parts
                        or member.name.startswith("/")
                        or any(ord(char) < 32 or ord(char) == 127 for char in member.name)
                        or not (member.isdir() or member.isreg())
                        or member.sparse is not None
                        or parts in seen
                        or member.size < 0
                    ):
                        raise TransferError("Unsafe archive entry; only regular files and directories are allowed.")
                    seen.add(parts)
                    total += member.size
                    members.append(member)
                    if len(members) > self.MAX_MEMBERS or total > self.MAX_BYTES:
                        raise TransferError("Directory exceeds the 100000-entry or 100-GiB limit.")
        except tarfile.TarError as exc:
            raise TransferError("Invalid directory archive.") from exc
        if not any(PurePosixPath(item.name).parts == (name,) and item.isdir()
                   for item in members):
            raise TransferError("Recursive source must be a directory.")
        return members

    def publish(self, archive_path: Path, directory: Path, name: str) -> None:
        """Stage a validated tree privately, then rename it into place."""
        if not directory.is_dir():
            raise TransferError("Destination directory does not exist.")
        destination = directory / name
        if destination.exists() or destination.is_symlink():
            raise TransferError("Destination subtree already exists; recursive merge is not supported.")
        members = self.validate(archive_path, name)
        with tempfile.TemporaryDirectory(prefix=".dwlab-scp-tree-", dir=directory) as staging:
            root = Path(staging)
            with tarfile.open(archive_path, "r:") as archive:
                for member in members:
                    parts = PurePosixPath(member.name).parts
                    parent = root
                    directory_parts = parts if member.isdir() else parts[:-1]
                    for component in directory_parts:
                        parent = parent / component
                        parent.mkdir(mode=0o700, exist_ok=True)
                        parent.chmod(0o700)
                    if member.isdir():
                        continue
                    output_path = root.joinpath(*parts)
                    mode = 0o700 if member.mode & 0o100 else 0o600
                    descriptor = os.open(output_path, os.O_WRONLY | os.O_CREAT |
                                         os.O_EXCL | os.O_NOFOLLOW, mode)
                    with os.fdopen(descriptor, "wb") as output:
                        with archive.extractfile(member) as source:
                            shutil.copyfileobj(source, output)
                    output_path.chmod(mode)
            if destination.exists() or destination.is_symlink():
                raise TransferError("Destination subtree already exists.")
            os.rename(root / name, destination)

    def receive(self, directory: Path, name: str, checksum: str) -> None:
        """Receive an SSH stream, verify it, then publish the validated tree."""
        if not directory.is_dir():
            raise TransferError("Destination directory does not exist.")
        with tempfile.TemporaryDirectory(prefix=".dwlab-scp-upload-", dir=directory) as staging:
            archive = Path(staging) / "payload.tar"
            descriptor = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as output:
                shutil.copyfileobj(sys.stdin.buffer, output)
            if self.digest(archive) != checksum:
                raise TransferError("Transfer checksum mismatch.")
            self.publish(archive, directory, name)


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

    def __init__(
        self, runner: Callable = subprocess.run, *,
        jump: str | None = None, source_jump: str | None = None,
        destination_jump: str | None = None,
    ) -> None:
        self._runner = runner
        self._source_jump = self._validate_jump(source_jump if source_jump is not None else jump)
        self._destination_jump = self._validate_jump(
            destination_jump if destination_jump is not None else jump
        )

    def copy(self, source: str, destination: str, *, recursive: bool = False) -> int:
        """Copy a remote source or filename pattern; return the transfer count."""
        origin = RemoteLocation.parse(source)
        target = RemoteLocation.parse(destination) if ":" in destination else None
        if any(char in origin.path for char in "*?[]"):
            if recursive or origin.path.endswith("/"):
                raise TransferError("Filename wildcards cannot be combined with recursive copying.")
            origins = self._matching_sources(origin)
        else:
            origins = [origin]
        for item in origins:
            self._copy_one(item, target, destination, recursive=recursive)
        return len(origins)

    def _matching_sources(self, origin: RemoteLocation) -> list[RemoteLocation]:
        directory = PurePosixPath(origin.path).parent
        pattern = PurePosixPath(origin.path).name
        if any(char in str(directory) for char in "*?[]"):
            raise TransferError("Wildcards are supported only in the filename, not directory paths.")
        command = shlex.join([
            "sudo", "-n", "find", str(directory), "-mindepth", "1",
            "-maxdepth", "1", "-type", "f", "-name", pattern, "-print0",
        ])
        result = self._ssh(
            origin.host, command, jump=self._source_jump,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        )
        manifest = result.stdout
        if not manifest:
            raise TransferError(f"No regular files match the source pattern: {origin.path}")
        if not manifest.endswith(b"\0"):
            raise TransferError("Invalid source file listing.")
        entries = manifest[:-1].split(b"\0")
        if len(entries) > 1000:
            raise TransferError("Source pattern matches more than 1000 files; narrow the pattern.")
        origins = []
        seen = set()
        for entry in entries:
            path = os.fsdecode(entry)
            parsed = RemoteLocation.parse(f"{origin.host}:{path}")
            member = PurePosixPath(parsed.path)
            if (member.parent != directory or path in seen
                    or not fnmatch.fnmatchcase(member.name, pattern)):
                raise TransferError("Unexpected entry in source file listing.")
            seen.add(path)
            origins.append(parsed)
        return sorted(origins, key=lambda item: item.path)

    def _copy_one(self, origin: RemoteLocation, target: RemoteLocation | None,
                  destination: str, *, recursive: bool) -> None:
        name = PurePosixPath(origin.path).name
        if (origin.path.endswith("/") and not recursive) or name in {"", ".", ".."}:
            raise TransferError("Specify a named source; use -r for a directory.")
        with tempfile.TemporaryDirectory(prefix="dwlab-scp-") as staging:
            staged_file = Path(staging) / "payload"
            descriptor = os.open(staged_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as output:
                source_command = ["sudo", "-n", "cat", "--", origin.path]
                if recursive:
                    source_command = [
                        "sudo", "-n", "tar", "--format=pax", "-C",
                        str(PurePosixPath(origin.path).parent), "-cf", "-", "--", name,
                    ]
                self._ssh(
                    origin.host,
                    shlex.join(source_command),
                    jump=self._source_jump, stdin=subprocess.DEVNULL, stdout=output,
                )
            if recursive:
                self._copy_tree(staged_file, target, destination, name)
                return
            if target:
                command = shlex.join([
                    "sh", "-c", self._PUBLISH_SCRIPT, "dwlab-scp",
                    target.path, name, self._digest(staged_file),
                ])
                with staged_file.open("rb") as input_file:
                    self._ssh(target.host, command, jump=self._destination_jump, stdin=input_file,
                              stdout=subprocess.DEVNULL)
            else:
                self._publish_local(staged_file, Path(destination), name)

    def _digest(self, path: Path) -> str:
        return TreeArchive().digest(path)

    def _validate_jump(self, value: str | None) -> str | None:
        if value is None or value == "none":
            return None
        pattern = r"(?:[A-Za-z0-9_][A-Za-z0-9_.-]*@)?[A-Za-z0-9_][A-Za-z0-9_.-]*(?::[0-9]{1,5})?"
        if not value or not all(re.fullmatch(pattern, item) for item in value.split(",")):
            raise TransferError("Invalid jump host; use [user@]host[:port] or comma-separated hops.")
        return value

    def _copy_tree(self, archive: Path, target: RemoteLocation | None,
                   destination: str, name: str) -> None:
        tree = TreeArchive()
        tree.validate(archive, name)
        if target is None:
            tree.publish(archive, Path(destination), name)
            return
        # Ship the same installed validator, not a second remote implementation.
        program = (
            "import hashlib, os, shutil, sys, tarfile, tempfile\n"
            "from pathlib import Path, PurePosixPath\n"
            + inspect.getsource(TransferError) + "\n"
            + inspect.getsource(TreeArchive) + "\n"
            "try:\n"
            "    TreeArchive().receive(Path(sys.argv[1]), sys.argv[2], sys.argv[3])\n"
            "except (TransferError, OSError, tarfile.TarError) as exc:\n"
            "    print(str(exc), file=sys.stderr)\n"
            "    sys.exit(1)\n"
        )
        command = shlex.join(["python3", "-c", program, target.path, name, tree.digest(archive)])
        with archive.open("rb") as source:
            self._ssh(target.host, command, jump=self._destination_jump,
                      stdin=source, stdout=subprocess.DEVNULL)

    def _ssh(self, host: str, command: str, *, jump: str | None = None,
             **streams) -> subprocess.CompletedProcess:
        options = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15"]
        if jump:
            options.extend(["-J", jump])
        try:
            return self._runner(
                options + ["--", host, command],
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
            description="Copy a remote file or directory using source sudo.",
        )
        parser.add_argument("-r", "--recursive", action="store_true", help="Copy a directory subtree")
        parser.add_argument("-J", "--jump", help="SSH jump host(s) for both endpoints")
        parser.add_argument("--source-jump", help="Override source jump host(s); 'none' for direct")
        parser.add_argument("--destination-jump", help="Override destination jump host(s); 'none' for direct")
        parser.add_argument("source", help="USER@HOST:/absolute/path (quote filename wildcards)")
        parser.add_argument("destination", help="Local directory or USER@HOST:/directory")
        args = parser.parse_args(argv)
        logger = logging.Logger("dwlab-scp")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("dwlab-scp.sh: %(message)s"))
        logger.addHandler(handler)
        try:
            logger.info("Transfer started.")
            transfer = SecureTransfer(
                jump=args.jump, source_jump=args.source_jump,
                destination_jump=args.destination_jump,
            )
            count = transfer.copy(
                args.source, args.destination, recursive=args.recursive
            )
        except (TransferError, OSError, tarfile.TarError) as exc:
            logger.error("Transfer failed: %s", exc)
            return 1
        except KeyboardInterrupt:
            logger.error("Transfer interrupted.")
            return 130
        logger.info("Transfer completed successfully: %s item(s) (private permissions).", count)
        return 0


if __name__ == "__main__":
    raise SystemExit(TransferCli().run())
