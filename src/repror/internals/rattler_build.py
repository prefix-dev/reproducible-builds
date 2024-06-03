import os

from repror.internals.commands import run_command


def get_rattler_build():
    if "RATTLER_BUILD_BIN" in os.environ:
        return os.environ["RATTLER_BUILD_BIN"]
    else:
        return "rattler-build"


def build_rattler(clone_dir):
    build_command = ["cargo", "build", "--release"]

    run_command(build_command, cwd=clone_dir)


def rattler_build_version(cwd):
    rattler_bin = get_rattler_build()

    command = [rattler_bin, "-V"]

    run_command(command, cwd=str(cwd))
