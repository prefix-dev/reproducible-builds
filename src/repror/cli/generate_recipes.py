import json
from repror.internals import config
from repror.internals.options import global_options


def generate_recipes():
    """Generate list of recipes from the configuration file."""
    # Prepare the matrix
    all_recipes = config.load_all_recipes(global_options.config_path)

    recipe_list = [recipe.name for recipe in all_recipes]

    # Convert the matrix to JSON
    recipe_list = json.dumps(recipe_list)
    print(recipe_list)
