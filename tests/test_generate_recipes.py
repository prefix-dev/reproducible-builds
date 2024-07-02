from pathlib import Path

from repror.cli.generate_recipes import _generate_recipes


# Uses the `db_access` fixture
def test_generate_recipes_all(db_access):
    # The seeding of the database,
    # includes a built/rebuilt boltons recipe
    recipes = _generate_recipes(
        rattler_build_hash=db_access.build_tool_hash,
        all_=True,
        config_path=Path(__file__).parent / "data" / "just_boltons.yaml",
    )
    # Even though boltons is build because of `-all`
    # it should still be in the list
    assert recipes == ["boltons"]


def test_generate_recipes_unfinished(db_access):
    # The seeding of the database,
    # includes a built/rebuilt boltons recipe
    recipes = _generate_recipes(
        rattler_build_hash=db_access.build_tool_hash,
        all_=False,
        config_path=Path(__file__).parent / "data" / "just_boltons.yaml",
    )
    # boltons is already built, so it should not be in the list
    assert recipes == []
