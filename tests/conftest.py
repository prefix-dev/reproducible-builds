from pathlib import Path
import pytest


@pytest.fixture
def setup_recipe_directory(tmp_path: Path):
    # Create directories
    recipe_folder = tmp_path / "recipe_folder"
    recipe_folder.mkdir()

    boltons_recipe = Path(__file__).parent / "data" / "boltons_recipe.yaml"

    (recipe_folder / "recipe.yaml").write_text(boltons_recipe.read_text())

    sub_dir = recipe_folder / "subfolder"
    sub_dir.mkdir()

    # Create files
    (sub_dir / "script.sh").write_text("echo hellooo")

    return recipe_folder
