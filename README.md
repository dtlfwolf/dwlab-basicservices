# DW-Lab Basic Services

This standalone Debian package provides the shared shell helpers and environment
profiles used by DW-Lab products. Version 0.22.0 provides secure file and subtree
transfer using Bash, system Python 3, OpenSSH client and coreutils. It does not
install wheels, a virtual environment or a compiler toolchain.

## Secure File Transfer (0.22.0)

Run this on your workstation (not with local sudo):

```bash
/opt/dwlab/dwlab-basicservices/bin/dwlab-scp.sh \
  dwlab@dwlab-cmkdev.dw-lab.de:/var/lib/dwlab/dwlab-cmkcentralserver/packages/dwlab-dwhome-cmkdev-dw-lab.com-2.4.0p35-0.7.12+generator0.5.9.deb \
  dwlab@dwlab-cmkdev-dwhome.dwhome.de:/tmp/
```

The command is also on PATH after a new login or sourcing
`/etc/profile.d/dwlab-basicservices.sh`. Install this basicservices package on
the initiating workstation; neither remote endpoint needs the helper installed.
The remote source needs sudo and cat; recursive reads additionally need GNU tar.
The remote destination needs a POSIX shell and coreutils, including mktemp,
sha256sum and mv. Recursive remote destinations additionally require Python 3.10
or newer; the installed validator is sent over SSH, not installed on that host.
Source and destination require working noninteractive SSH authentication and
verified host keys. Configure usernames, keys, ports or jump hosts in
`~/.ssh/config`; the tool never disables host verification or forwards an agent.
The source user needs existing sudo permission to read the file with
`sudo -n cat -- /absolute/file`, or permission to run the source-side tar command
for recursive reads. No sudo policy is installed or expanded.

Use one exact source path, not globs, SCP URLs or
bracketed IPv6 addresses (use an SSH alias for IPv6). The destination must be an
existing writable directory, either local or remote. For a local copy, replace
the destination with `./` or another directory. Paths with spaces must be quoted.

### Jump Hosts And Recursive Copies

```bash
dwlab-scp.sh -r -J detlef@jump.example.org \
  dwlab@source.example.org:/protected/release-directory \
  dwlab@target.example.org:/tmp/
```

`-J [user@]host[:port]` applies to both source and destination connections.
Comma-separated jump chains are supported. Use SSH aliases for IPv6 jump hosts.
For different routes, use `--source-jump` and `--destination-jump`; the explicit
value `none` omits the command-line jump override for that endpoint (SSH config
still applies). For example, when only the destination requires a jump:

```bash
dwlab-scp.sh -r --destination-jump detlef@jump.example.org \
  dwlab@source.example.org:/protected/release-directory \
  dwlab@target.example.org:/tmp/
```

`-r` copies the named directory, including hidden files and empty directories,
to `<destination-directory>/<source-basename>`. Existing same-name files,
directories or symlinks are refused: there is no recursive merge or replacement.
The source root itself cannot be `/`. Symlinks, hardlinks, sparse archive entries,
special files, duplicate entries, control-character names and path traversal are
rejected before destination transfer. The validator allows at most 100000 archive
entries and 100 GiB of logical file content. The source should be quiescent;
this is a transfer helper, not a consistent live-filesystem backup.

Directories receive mode 0700; files receive 0600, or 0700 if the source file has
owner execute permission. Group/other access and privileged mode bits are never
preserved. Ownership is the destination login identity. This protects private
keys but intentionally differs from a metadata-preserving `scp -r` or backup.

Local staging uses
a private temporary directory and file. A failed source read never publishes a
partial destination. Single-file publication uses a mode-0600 temporary file
and atomic replacement in the destination directory, with SHA-256 verification
before remote publication; a final-path symlink is
replaced, not followed. Existing same-name files are replaced in single-file
mode only. Recursive transfers use a validated tar stream, manual regular-file
extraction into a private directory and a final rename; no `extractall` or
unvalidated remote tar extraction is used. Remote uploads are checked against
SHA-256 before extraction. The caller must
trust the destination directory and its owner; private workstation directories
are preferred. Source modes and directory permissions remain unchanged.
Normal completion and failures clean up local staging; remote staging is cleaned
on normal completion, command failure and handled signals. SIGKILL, host crashes
or power loss can leave private staging files requiring administrator cleanup.
Single-file mode copies only file bytes, not ownership, timestamps or executable
permissions. Recursive mode retains owner execute only, as described above.
Install packages with sudo on the target afterwards, then remove transfer copies.
Errors go to stderr and return status 1 (interruption 130, usage error 2).

## Shared Python Profile (0.20.1)

The package now explicitly owns `/etc/profile.d/dwlab-python.sh` as a conffile.
Previously that file was generated by the older Python installation scripts,
not delivered by `dwlab-basicservices 0.20.0`. The bundled-runtime installation
path could therefore leave it missing on a fresh host.

The profile exports `DWLAB_PYTHON_VENV=/opt/dwlab/venv` and adds its `bin` directory
to `PATH` only when it exists. Repeated sourcing does not duplicate the entry.
It does not activate the virtual environment or change `VIRTUAL_ENV`. An inherited
`DWLAB_PYTHON_VENV` cannot redirect this system-wide profile to an untrusted path.
The runtime and its parent directories must be maintained by the administrator.

## Build And Verify

Supply the independently available DW-Lab build-helper directory explicitly:

```bash
make DWLAB_HELPERS_ROOT=/path/to/dwlab-helpers PACKAGES_DIR=/path/to/artifacts build
python3 -m pytest -q tests
dpkg-deb -c /path/to/artifacts/dwlab-basicservices_0.22.0_all.deb
```

The regression tests require Bash, Python/pytest and the standard Debian
`dpkg-deb` utility. They extract a disposable DEB without installing it and test
the delivered profile in isolated shells; no root or source checkouts of other
DW-Lab products are required.

## Install, Upgrade And Remove

```bash
sudo apt install ./dwlab-basicservices_0.22.0_all.deb
dpkg-query -S /etc/profile.d/dwlab-python.sh
. /etc/profile.d/dwlab-python.sh
command -v dwlabovpn
```

The last command succeeds only if the separate OpenVPN runtime is installed.
New login shells read the profile automatically. Existing shells must source
it or log in again; re-login cannot repair an absent file. On upgrade, normal
dpkg conffile handling preserves locally modified configuration. Review any
existing profile left by the older installer rather than overwriting it silently.

Removing this package does not remove the separately managed Python runtime.
`apt remove dwlab-basicservices` retains conffiles; `apt purge` removes them.
Check dependent DW-Lab products before removing the shared shell environment.
