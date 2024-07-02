from dataclasses import dataclass
from pathlib import Path
import pytest
from sqlalchemy.orm import sessionmaker
from repror.cli.utils import platform_name, platform_version
from repror.internals.db import setup_local_db, Build, Rebuild, BuildState, RemoteRecipe
from sqlmodel import Session
from datetime import datetime
from unittest.mock import patch
from repror.internals.recipe import recipe_files_hash


@pytest.fixture
def setup_recipe_directory(tmp_path: Path):
    # Create directories
    recipe_folder = tmp_path / "recipe_folder"
    recipe_folder.mkdir()

    boltons_recipe = Path(__file__).parent / "data" / "boltons" / "boltons_recipe.yaml"

    (recipe_folder / "recipe.yaml").write_text(boltons_recipe.read_text())

    sub_dir = recipe_folder / "subfolder"
    sub_dir.mkdir()

    # Create files
    (sub_dir / "script.sh").write_text("echo hellooo")

    return recipe_folder


@pytest.fixture
def test_config_yaml_path():
    return Path(__file__).parent / "data" / "test_config.yaml"


@pytest.fixture(scope="session")
def in_memory_session():
    return setup_local_db()


@dataclass
class DbAccess:
    # Fake time for the builds
    build_time_1: datetime
    build_time_2: datetime
    # rattler-build hash
    build_tool_hash: str
    # Session to be used by the tests
    session: Session


@pytest.fixture(scope="session")
def seed_db(in_memory_session):
    with in_memory_session() as session:
        seed_build_rebuild(session)
        seed_recipes(session)
        session.commit()


@pytest.fixture(scope="function")
def db_access(in_memory_session: sessionmaker[Session], seed_db):
    with patch("repror.internals.db.get_session", return_value=in_memory_session()):
        with in_memory_session() as session:
            yield DbAccess(
                build_time_1=timestamp1,
                build_time_2=timestamp2,
                build_tool_hash=build_tool_hash,
                session=session,
            )
            session.rollback()


def seed_recipes(session: Session):
    # Insert some Recipes
    recipe = RemoteRecipe(
        url="foobar",
        rev="asdfsdf",
        name="foo",
        content_hash="1234",
        path="bar",
        raw_config="raw",
    )
    recipe2 = RemoteRecipe(
        url="foobarz",
        rev="asdfsdf",
        name="foobar",
        content_hash="12345",
        path="bar",
        raw_config="raw",
    )
    session.add(recipe)
    session.add(recipe2)


# Define a couple of timestamps
timestamp1 = datetime(2023, 1, 1, 12, 0, 0)
timestamp2 = datetime(2023, 6, 1, 12, 0, 0)
build_tool_hash = "rattler-build"


def seed_build_rebuild(session: Session):
    # Sample Build and Rebuild data
    boltons_hash = recipe_files_hash(Path(__file__).parent / "data" / "boltons")
    builds = [
        Build(
            id=1,
            recipe_name="boltons",
            state=BuildState.SUCCESS,
            build_tool_hash=build_tool_hash,
            recipe_hash=boltons_hash,
            platform_name=platform_name(),
            platform_version=platform_version(),
            build_hash="bh1",
            build_loc="loc1",
            reason=None,
            timestamp=timestamp1,
            actions_url="url1",
        ),
        Build(
            id=2,
            recipe_name="Recipe2",
            state=BuildState.SUCCESS,
            build_tool_hash=build_tool_hash,
            recipe_hash="rhash2",
            platform_name=platform_name(),
            platform_version=platform_version(),
            build_hash="bh2",
            build_loc="loc2",
            reason=None,
            timestamp=timestamp2,
            actions_url="url2",
        ),
        Build(
            id=3,
            recipe_name="Recipe3",
            state=BuildState.SUCCESS,
            build_tool_hash=build_tool_hash,
            recipe_hash="rhash3",
            platform_name=platform_name(),
            platform_version=platform_version(),
            build_hash="bh3",
            build_loc="loc3",
            reason=None,
            timestamp=timestamp2,
            actions_url="url3",
        ),
        Build(
            id=4,
            recipe_name="Recipe4",
            state=BuildState.SUCCESS,
            build_tool_hash=build_tool_hash,
            recipe_hash="rhash4",
            platform_name=platform_name(),
            platform_version=platform_version(),
            build_hash="bh4",
            build_loc="loc4",
            reason=None,
            timestamp=timestamp2,
            actions_url="url4",
        ),
        Build(
            id=5,
            recipe_name="Recipe4Fail",
            state=BuildState.FAIL,
            build_tool_hash=build_tool_hash,
            recipe_hash="rhash4",
            platform_name=platform_name(),
            platform_version=platform_version(),
            build_hash="bh4",
            build_loc="loc4",
            reason=None,
            timestamp=timestamp2,
            actions_url="url4",
        ),
    ]

    rebuilds = [
        Rebuild(
            id=1,
            build_id=1,
            state=BuildState.SUCCESS,
            reason="Fix issue",
            rebuild_hash="rbhash1",
            timestamp=timestamp1,
            actions_url="rebuild_url1",
        ),
        Rebuild(
            id=2,
            build_id=2,
            state=BuildState.SUCCESS,
            reason="Update dependencies",
            rebuild_hash="rbhash2",
            timestamp=timestamp2,
            actions_url="rebuild_url2",
        ),
        Rebuild(
            id=3,
            build_id=3,
            state=BuildState.SUCCESS,
            reason="Security patch",
            rebuild_hash="rbhash3",
            timestamp=timestamp2,
            actions_url="rebuild_url3",
        ),
        Rebuild(
            id=4,
            build_id=4,
            state=BuildState.SUCCESS,
            reason="Performance improvement",
            rebuild_hash="rbhash4",
            timestamp=timestamp2,
            actions_url="rebuild_url4",
        ),
    ]

    session.add_all(builds)
    session.add_all(rebuilds)
