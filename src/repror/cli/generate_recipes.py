import json
from repror.internals import conf


def generate_recipes():
    """Generate list of recipes from the configuration file."""
    # Prepare the matrix

    all_recipes = conf.load_all_recipes()

    recipe_list = [recipe.name for recipe in all_recipes]

    # Convert the matrix to JSON
    recipe_list = json.dumps(recipe_list)
    print(recipe_list)
