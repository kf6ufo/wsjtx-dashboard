"""Owner-only permissions for explicitly selected configuration/state paths."""
import os
from pathlib import Path
import sqlite3
import stat


def private_directory(path):
    """Create missing private parents; tighten only the named existing directory."""
    path = Path(path)
    try:
        path.mkdir(mode=0o700)
    except FileNotFoundError:
        private_directory(path.parent)
        path.mkdir(mode=0o700, exist_ok=True)
    except FileExistsError:
        pass
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fchmod(fd, 0o700)
    finally:
        os.close(fd)


def private_file(path, flags=os.O_RDONLY):
    """Return a regular-file descriptor, without following links or truncating data.

    The caller owns the descriptor. Creation flags must be explicit; permissions
    are applied before callers write secrets or SQLite opens a new database.
    """
    fd = os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('Private configuration/state must be a regular file')
        os.fchmod(fd, 0o600)
    except BaseException:
        os.close(fd)
        raise
    return fd


def private_database(path):
    path = Path(path)
    private_directory(path.parent)
    os.close(private_file(path, os.O_RDWR | os.O_CREAT))
    # Existing SQLite sidecars can survive an interrupted process. Do not scan
    # the directory or touch unrelated files; SQLite creates new sidecars at 0600.
    for suffix in ('-wal', '-shm', '-journal'):
        sidecar = path.with_name(path.name + suffix)
        if sidecar.exists() or sidecar.is_symlink():
            os.close(private_file(sidecar))
    return sqlite3.connect(path, check_same_thread=False)
