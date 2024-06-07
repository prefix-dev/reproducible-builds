from repror.internals.conf import load_all_recipes
from pathlib import Path


def test_load_all_recipes_test():
    """Check to see if all recipes can be loaded"""
    recipes = load_all_recipes(Path(__file__).parent.parent / "config.yaml")
    for r in recipes:
        if r.is_local():
            assert r.path == r.local_path
        else:
            assert r.path == r._remote_path
