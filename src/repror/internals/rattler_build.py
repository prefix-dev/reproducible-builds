import hashlib
import os

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


def rattler_build_version(cwd):
    rattler_bin = get_rattler_build()

    command = [rattler_bin, "-V"]

    run_command(command, cwd=str(cwd))


def rattler_build_hash():
    config = load_config()
    url, rev = config.rattler_build.url, config.rattler_build.rev
    return hashlib.sha256(f"{url}{rev}".encode()).hexdigest()
