import json
from repror.internals import conf


def generate_recipes():
    """Generate list of recipes from the configuration file."""
    # Prepare the matrix
    recipe_list = []

    config = conf.load_config()

    # Parse repositories and local paths
    for repo in config.get("repositories", []):
        url = repo["url"]
        branch = repo["branch"]
        for recipe in repo.get("recipes", []):
            path = recipe["path"]
            recipe_list.append(f"{url}::{branch}::{path}")

    for local in config.get("local", []):
        path = local["path"]
        recipe_list.append(f"local::local::{path}")

    # Convert the matrix to JSON
    recipe_list = json.dumps(recipe_list)
    print(recipe_list)
