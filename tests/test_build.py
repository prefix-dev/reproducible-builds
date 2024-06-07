from typer.testing import CliRunner

from repror.repror import app

runner = CliRunner()


def test_build_boltons():
    result = runner.invoke(app, ["build-recipe", "boltons"])
    assert result.exit_code == 0


def test_rebuild_build_boltons():
    result = runner.invoke(app, ["rebuild-recipe", "boltons"])
    assert result.exit_code == 0
