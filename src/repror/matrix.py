

import json
from repror import conf


if __name__ == "__main__":
    # Prepare the matrix
    matrix = []

    config = conf.load_config()

    # Parse repositories and local paths
    for repo in config.get('repositories', []):
        url = repo['url']
        branch = repo['branch']
        for recipe in repo.get('recipes', []):
            path = recipe['path']
            matrix.append(f"{url}::{branch}::{path}")

    for local in config.get('local', []):
        path = local['path']
        matrix.append(matrix.append(f"local::local::{path}"))

    # Convert the matrix to JSON
    matrix_json = json.dumps(matrix)
    print(matrix_json)