from typer.testing import CliRunner

from repror.repror import app

runner = CliRunner()


def test_build_boltons():
    """Build boltons recipe, last run should be cached"""
    result = runner.invoke(app, ["--in-memory-sql", "build-recipe", "boltons"])
    assert result.exit_code == 0, result.stdout
    result = runner.invoke(app, ["--in-memory-sql", "build-recipe", "boltons"])
    assert "Found latest build" in result.stdout


def test_rebuild_build_boltons():
    """Rebuild boltons recipe, last run should be cached"""
    result = runner.invoke(app, ["--in-memory-sql", "rebuild-recipe", "boltons"])
    assert result.exit_code == 0, result.stdout
    result = runner.invoke(app, ["--in-memory-sql", "rebuild-recipe", "boltons"])
    assert "Found latest rebuild" in result.stdout
