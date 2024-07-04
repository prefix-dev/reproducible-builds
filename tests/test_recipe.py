from repror.internals.config import load_all_recipes
from pathlib import Path
from typer.testing import CliRunner


from repror.internals.db import RemoteRecipe


runner = CliRunner()


def test_load_all_recipes_test():
    """Check to see if all recipes can be loaded"""
    recipes = load_all_recipes(Path(__file__).parent.parent / "config.yaml")
    remote_recipe = next(
        filter(lambda recipe: isinstance(recipe, RemoteRecipe), recipes.all_recipes)
    )
    with remote_recipe.local_path as local_path:
        assert Path(local_path).exists()


# def test_recipe_files_hash(setup_recipe_directory: Path):
#     initial_content_hash = recipe_files_hash(setup_recipe_directory)

#     # modify build script
#     build_script = setup_recipe_directory / "subfolder" / "script.sh"
#     build_script.write_text("echo hellooo\n echo this is test")

#     # Calculate the hash using the recipe_files_hash function
#     modified_hash = recipe_files_hash(setup_recipe_directory)

#     assert initial_content_hash != modified_hash
