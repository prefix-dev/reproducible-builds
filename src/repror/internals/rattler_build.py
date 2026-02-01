import hashlib
import os
import subprocess

from repror.internals.commands import run_command, run_streaming_command
from repror.internals.config import load_config


def get_rattler_build():
    if "RATTLER_BUILD_BIN" in os.environ:
        return os.environ["RATTLER_BUILD_BIN"]
    else:
        return "rattler-build"


def build_rattler(clone_dir):
    build_command = ["cargo", "build", "--release"]

    run_streaming_command(build_command, cwd=clone_dir)


def rattler_build_version(cwd=None):
    """Get the rattler-build version string."""
    rattler_bin = get_rattler_build()
    command = [rattler_bin, "-V"]

    if cwd:
        run_command(command, cwd=str(cwd))
    else:
        result = subprocess.run(command, capture_output=True, text=True)
        return result.stdout.strip()


def get_rattler_build_version_string() -> str:
    """Get the version string from rattler-build -V."""
    rattler_bin = get_rattler_build()
    try:
        result = subprocess.run(
            [rattler_bin, "-V"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def rattler_build_hash():
    """Compute a hash identifying the rattler-build version.

    Uses config.yaml if available (for source builds), otherwise
    falls back to the installed rattler-build version string.
    """
    config = load_config()
    if config.rattler_build:
        # Use config-based hash for source builds
        url, rev = config.rattler_build.url, config.rattler_build.rev
        return hashlib.sha256(f"{url}{rev}".encode()).hexdigest()
    else:
        # Use version string for released builds
        version = get_rattler_build_version_string()
        return hashlib.sha256(version.encode()).hexdigest()
