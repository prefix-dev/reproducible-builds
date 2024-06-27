from repror.internals.db import RemoteRecipe, get_total_unique_recipes, setup_local_db


def test_recipe_db():
    session_maker = setup_local_db()
    with session_maker() as session:
        # Insert some Recipes
        recipe = RemoteRecipe(url="foobar", rev="asdfsdf", name="foo", content_hash="1234", path="bar", raw_config="raw")
        recipe2 = RemoteRecipe(url="foobarz", rev="asdfsdf", name="foobar", content_hash="12345", path="bar", raw_config="raw")
        session.add(recipe)
        session.add(recipe2)
        session.commit()

    assert get_total_unique_recipes(session) == 2
