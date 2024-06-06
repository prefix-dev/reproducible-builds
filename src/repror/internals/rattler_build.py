import hashlib
import os

from repror.internals.commands import run_command, run_streaming_command_stderr
from repror.internals.conf import load_config


def get_rattler_build():
    if "RATTLER_BUILD_BIN" in os.environ:
        return os.environ["RATTLER_BUILD_BIN"]
    else:
        return "rattler-build"


def build_rattler(clone_dir):
    build_command = ["cargo", "build", "--release"]

    run_streaming_command_stderr(build_command, cwd=clone_dir)


def rattler_build_version(cwd):
    rattler_bin = get_rattler_build()

    command = [rattler_bin, "-V"]

    run_command(command, cwd=str(cwd))


def rattler_build_hash():
    config = load_config()
    rattler_build_config = config["rattler-build"]
    url, rev = rattler_build_config["url"], rattler_build_config["rev"]
    return hashlib.sha256(f"{url}{rev}".encode()).hexdigest()
