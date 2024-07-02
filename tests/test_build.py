from typer.testing import CliRunner
from unittest.mock import Mock, patch
from repror.repror import app

runner = CliRunner()


@patch("repror.internals.build.build_conda_package")
@patch("repror.internals.build.find_conda_file")
def test_build_boltons(find_conda_file_mock, build_conda_package_mock, tmp_path):
    """Build boltons recipe, last run should be cached"""
    mock_output = Mock()
    mock_output.return_code = 0

    build_conda_package_mock.return_value = mock_output

    conda_file = tmp_path / "some_output.conda"
    conda_file.touch()

    find_conda_file_mock.return_value = conda_file

    result = runner.invoke(
        app, ["--in-memory-sql", "build-recipe", "boltons"], catch_exceptions=False
    )

    assert result.exit_code == 0, result.stdout
    result = runner.invoke(
        app, ["--in-memory-sql", "build-recipe", "boltons"], catch_exceptions=False
    )

    assert "Already Built" in result.stdout


@patch("repror.internals.build.rebuild_conda_package")
@patch("repror.internals.build.build_conda_package")
@patch("repror.internals.build.find_conda_file")
def test_rebuild_build_boltons(
    find_conda_file_mock, build_conda_package_mock, rebuild_conda_package_mock, tmp_path
):
    """Rebuild boltons recipe, last run should be cached"""
    mock_output = Mock()
    mock_output.return_code = 0

    build_conda_package_mock.return_value = mock_output

    return_mock = Mock()
    return_mock.return_code = 0

    rebuild_conda_package_mock.return_value = return_mock

    conda_file = tmp_path / "some_output.conda"
    conda_file.touch()

    find_conda_file_mock.return_value = conda_file
    result = runner.invoke(
        app, ["--in-memory-sql", "rebuild-recipe", "boltons"], catch_exceptions=False
    )
    assert result.exit_code == 0, result.stdout
    result = runner.invoke(
        app, ["--in-memory-sql", "rebuild-recipe", "boltons"], catch_exceptions=False
    )
    assert "Found latest rebuild" in result.stdout
