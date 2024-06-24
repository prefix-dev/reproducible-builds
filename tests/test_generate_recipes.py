import json
from typer.testing import CliRunner

from repror.repror import app

runner = CliRunner()


def test_generate_recipes():
    """Generate recipe names and verify that it outputs only parseable list of names"""
    result = runner.invoke(
        app,
        [
            "--no-output",
            "generate-recipes",
        ],
    )
    list_of_names = json.loads(result.stdout)
    assert isinstance(list_of_names, list)
