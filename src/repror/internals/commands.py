from typing import Optional

import glob
import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from subprocess import CompletedProcess
import io
from enum import Enum


def run_command(command, cwd=None, env=None, silent=False) -> CompletedProcess:
    """Run a specific command."""
    return subprocess.run(command, cwd=cwd, env=env, check=True, capture_output=silent)


class StreamType(Enum):
    """Enum to specify the type of stream to capture."""
    STDOUT = 1
    STDERR = 2

    @property
    def is_stdout(self):
        return self == StreamType.STDOUT

    @property
    def is_stderr(self):
        return self == StreamType.STDERR


def run_streaming_command(
    command: list[str],
    cwd: Optional[list[str]],
    env: Optional[list[str]] = None,
    stream_type: StreamType = StreamType.STDERR,
):
    """Run a specific command and stream the output."""

    # We can only capture of stdout or stderr, not both
    # Otherwise it will block
    # See: https://stackoverflow.com/questions/18421757/live-output-from-subprocess-command

    if stream_type.is_stderr:
        kwarwgs = {"stderr": subprocess.PIPE}
    else:
        kwarwgs = {"stdout": subprocess.PIPE}

    with subprocess.Popen(command, cwd=cwd, env=env, **kwarwgs) as process:
        # Print stderr as it comes in
        for line in io.TextIOWrapper(
            process.stderr, encoding="utf-8"
        ):  # or another encoding
            print(line, end="")

        # Also print the other output if there is any

        out = process.stdout if stream_type.is_stderr else process.stderr
        if out:
            print(process.stdout.readline())


def calculate_hash(conda_file: Path):
    """Calculate the SHA-256 hash of a conda file."""
    with conda_file.open(mode="rb") as f:
        # Read the entire file
        data = f.read()
        # Calculate the SHA-256 hash
        build_hash = hashlib.sha256(data).hexdigest()

    return build_hash


def find_conda_file(build_folder: Path) -> Path:
    """Find the conda file in the build folder."""
    conda_file = glob.glob(str(build_folder) + "/**/*.conda", recursive=True)[0]

    return Path(conda_file)


def find_all_conda_files(build_folder: Path):
    """Find all conda files in the build folder."""
    return glob.glob(str(build_folder) + "/**/*.conda", recursive=True)


def move_file(conda_file: Path, destination_directory: Path) -> Path:
    # Make dirs if they don't exist
    os.makedirs(destination_directory, exist_ok=True)
    # Get the base filename
    filename = Path(os.path.basename(conda_file))

    # Move the file to the destination directory
    file_loc = destination_directory / filename
    shutil.move(conda_file, file_loc)

    return file_loc


def pixi_root() -> Optional[Path]:
    """Get the pixi root location"""
    pixi_root = os.environ.get("PIXI_PROJECT_ROOT")
    if pixi_root:
        return Path(pixi_root)
    return None
