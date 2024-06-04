import json
import tempfile
from repror.internals import conf


def generate_recipes():
    """Generate list of recipes from the configuration file."""
    # Prepare the matrix

    with tempfile.TemporaryDirectory() as tmp_dir:
        all_recipes = conf.load_all_recipes(tmp_dir)

    recipe_list = [recipe.__dict__ for recipe in all_recipes]

    # Convert the matrix to JSON
    recipe_list = json.dumps(recipe_list)
    print(recipe_list)
