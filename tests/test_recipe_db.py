from repror.internals.db import get_total_unique_recipes


# Use the db_access fixture
def test_recipe_db(db_access):
    assert get_total_unique_recipes(db_access.session) == 2
