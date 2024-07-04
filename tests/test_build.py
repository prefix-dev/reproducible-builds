import pytest
from typer.testing import CliRunner
from unittest.mock import Mock, patch
from repror.repror import app
from pathlib import Path

runner = CliRunner()


@patch("repror.internals.build.build_conda_package")
@patch("repror.internals.build.find_conda_file")
def test_build_boltons(
    find_conda_file_mock,
    build_conda_package_mock,
    test_config_yaml_path: Path,
    tmp_path,
):
    """Build boltons recipe, last run should be cached"""
    mock_output = Mock()
    mock_output.return_code = 0

    build_conda_package_mock.return_value = mock_output

    conda_file = tmp_path / "some_output.conda"
    conda_file.touch()

    find_conda_file_mock.return_value = conda_file

    result = runner.invoke(
        app,
        [
            "--in-memory-sql",
            "--config-path",
            test_config_yaml_path,
            "build-recipe",
            "boltons",
            "--rattler-build-exe",
            "non_existing",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.stdout
    result = runner.invoke(
        app,
        [
            "--in-memory-sql",
            "--config-path",
            test_config_yaml_path,
            "build-recipe",
            "boltons",
            "--rattler-build-exe",
            "non_existing",
        ],
        catch_exceptions=False,
    )

    assert "Already Built" in result.stdout


# Until we decouple the rebuild test to have already a seed-ed build recipe, we depend on the build test
@pytest.mark.depends(on=["test_build_boltons"])
@patch("repror.internals.build.rebuild_conda_package")
@patch("repror.internals.build.build_conda_package")
@patch("repror.internals.build.find_conda_file")
def test_rebuild_build_boltons(
    find_conda_file_mock,
    build_conda_package_mock,
    rebuild_conda_package_mock,
    test_config_yaml_path,
    tmp_path,
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
        app,
        [
            "--in-memory-sql",
            "--config-path",
            test_config_yaml_path,
            "rebuild-recipe",
            "boltons",
            "--rattler-build-exe",
            "non_existing",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.stdout
    result = runner.invoke(
        app,
        [
            "--in-memory-sql",
            "--config-path",
            test_config_yaml_path,
            "rebuild-recipe",
            "boltons",
            "--rattler-build-exe",
            "non_existing",
        ],
        catch_exceptions=False,
    )
    assert "Found latest rebuild" in result.stdout
