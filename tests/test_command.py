import pytest
from typing import List
from repror.internals.commands import (
    StreamType,
    run_streaming_command,
    StreamingCmdOutput,
)

# Example commands and expected outputs
COMMAND_SUCCESS = ["python", "-c", "print('Hello, World!')"]
COMMAND_ERROR = ["python", "-c", "import sys; sys.stderr.write('error'); sys.exit(1)"]
EXPECTED_SUCCESS = StreamingCmdOutput(
    stdout="Hello, World!\n", stderr="", return_code=0
)
EXPECTED_ERROR = StreamingCmdOutput(stdout="", stderr="error", return_code=1)


@pytest.mark.parametrize(
    "command, stream_type, expected_output",
    [
        (COMMAND_SUCCESS, StreamType.STDOUT, EXPECTED_SUCCESS),
        (COMMAND_ERROR, StreamType.STDERR, EXPECTED_ERROR),
    ],
)
def test_run_streaming_command(
    command: List[str], stream_type: StreamType, expected_output: StreamingCmdOutput
) -> None:
    result = run_streaming_command(command, stream_type=stream_type)
    assert result.return_code == expected_output.return_code
    assert result.stderr == expected_output.stderr
    assert result.stdout == expected_output.stdout
