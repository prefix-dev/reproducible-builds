from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import logging
import os
from pathlib import Path
import tempfile
from typing import Generator, Optional
from pydantic import BaseModel
from sqlalchemy import func, text
from typing import Sequence
from sqlalchemy.orm import sessionmaker
from sqlmodel import (
    Field,
    Relationship,
    SQLModel,
    and_,
    create_engine,
    distinct,
    or_,
    select,
    Session as SqlModelSession,
    col,
    literal,
)

from repror.internals.recipe import clone_remote_recipe
from .print import print
from .options import global_options


# Suppress SQLAlchemy INFO logs
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

engine = None
# Create a session class that binds to SQLModelSession
__Session = sessionmaker(class_=SqlModelSession, expire_on_commit=False)

# Name of the production database
PROD_DB = "repro.db"


# Function to compute the hash of the build tool version and recipe
def compute_hash(value: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(value.encode("utf-8"))
    return hasher.hexdigest()


class BuildState(str, Enum):
    SUCCESS = "success"
    FAIL = "fail"


def create_db_and_tables():
    """Create the database and tables, if they don't exist."""
    __set_engine()
    assert engine  # This should not fail
    SQLModel.metadata.create_all(engine)


def setup_engine(in_memory: bool = False):
    """Setup the sqlite engine."""
    print(f"Setting up engine with in_memory={in_memory}")
    global engine, __Session
    if engine:
        # Engine is already set, skip initialization
        return

    if in_memory:
        engine = create_engine("sqlite:///:memory:", echo=False)
    else:
        # Get the name of the database from an environment variable
        # or use the default name which is a local database
        sqlite_file_name = os.getenv("REPRO_DB_NAME", "repro.local.db")
        # Do a manual check for safety
        if sqlite_file_name == PROD_DB:
            print("[dim yellow]Running on production[/dim yellow]")
        else:
            print(f"[dim green]Running on {sqlite_file_name}[/dim green]")

        # Setup the engine
        # We assume that the database is in the same directory as the project
        sqlite_url = f"sqlite:///{sqlite_file_name}"
        engine = create_engine(sqlite_url, echo=False)

    __Session.configure(
        bind=engine,
    )
    create_db_and_tables()


def setup_local_db() -> sessionmaker[SqlModelSession]:
    """Setup in-mmory database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=True)
    session = sessionmaker(class_=SqlModelSession, expire_on_commit=False)
    session.configure(bind=engine)
    SQLModel.metadata.create_all(engine)
    return session


def __set_engine() -> None:
    global engine
    if not engine:
        setup_engine(global_options.in_memory_sql)


def get_session() -> SqlModelSession:
    """Get a new session."""
    __set_engine()
    return __Session()


class Build(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    recipe_name: str
    state: BuildState
    build_tool_hash: str
    recipe_hash: str
    platform_name: str
    platform_version: str
    build_hash: Optional[str] = None
    build_loc: Optional[str] = None
    reason: Optional[str] = None
    timestamp: Optional[datetime] = Field(
        default=None,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )
    actions_url: Optional[str] = None
    rebuilds: list["Rebuild"] = Relationship(back_populates="build")


class Rebuild(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    build_id: int = Field(foreign_key="build.id")
    state: BuildState
    reason: Optional[str] = None
    rebuild_hash: Optional[str] = None
    timestamp: Optional[datetime] = Field(
        default=None,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )
    actions_url: Optional[str] = None
    build: Build = Relationship(back_populates="rebuilds")

    @property
    def platform_name(self):
        return self.build.platform_name

    @property
    def recipe_name(self):
        return self.build.recipe_name


class Recipe(BaseModel):
    name: str
    path: str
    raw_config: str
    content_hash: str

    @property
    @contextmanager
    def local_path(self) -> Generator[str, None, None]:
        yield self.path


class RemoteRecipe(Recipe, SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str
    rev: str

    @property
    @contextmanager
    def local_path(self) -> Generator[str, None, None]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            clone_dir = Path(tmp_dir)
            path_to_recipe_folder = Path(self.path).parent
            repo_dir = clone_remote_recipe(
                self.url, self.rev, clone_dir, path_to_recipe_folder
            )
            recipe_path = repo_dir / path_to_recipe_folder
            yield str(recipe_path)


def get_latest_builds(
    recipe_names_and_hash: list[tuple[str, str]],
    build_tool_hash: str,
    platform_name: str,
    platform_version: str,
) -> dict[str, Build]:
    with get_session() as session:
        conditions = [
            (Build.recipe_name == recipe_name) & (Build.recipe_hash == recipe_hash)
            for recipe_name, recipe_hash in recipe_names_and_hash
        ]

        subquery = (
            select(
                Build.recipe_name,
                Build.recipe_hash,
                func.max(Build.timestamp).label("max_timestamp"),
            )
            .where(or_(*conditions))
            .where(Build.build_tool_hash == build_tool_hash)
            .where(Build.platform_name == platform_name)
            .where(Build.platform_version == platform_version)
            .group_by(Build.recipe_name, Build.recipe_hash)
        ).subquery()

        statement = (
            select(Build)
            .join(
                subquery,
                and_(
                    Build.recipe_name == subquery.c.recipe_name,
                    Build.recipe_hash == subquery.c.recipe_hash,
                    Build.timestamp == subquery.c.max_timestamp,
                ),
            )
            .order_by(col(Build.timestamp).desc())
        )
        builds = session.exec(statement).fetchall()
        return {build.recipe_name: build for build in builds}


def get_latest_build_with_rebuild(
    recipe_names_and_hash: list[tuple[str, str]],
    build_tool_hash: str,
    platform_name: str,
    platform_version: str,
) -> dict[str, tuple[Build, Optional[Rebuild]]]:
    with get_session() as session:
        conditions = [
            (Build.recipe_name == recipe_name) & (Build.recipe_hash == recipe_hash)
            for recipe_name, recipe_hash in recipe_names_and_hash
        ]

        subquery = (
            select(
                Build.recipe_name,
                Build.recipe_hash,
                func.max(Build.timestamp).label("max_timestamp"),
            )
            .where(or_(*conditions))
            .where(Build.build_tool_hash == build_tool_hash)
            .where(Build.platform_name == platform_name)
            .where(Build.platform_version == platform_version)
            .group_by(Build.recipe_name, Build.recipe_hash)
        ).subquery()

        statement = (
            select(Build)
            .join(
                subquery,
                and_(
                    Build.recipe_name == subquery.c.recipe_name,
                    Build.recipe_hash == subquery.c.recipe_hash,
                    Build.timestamp == subquery.c.max_timestamp,
                ),
            )
            .order_by(col(Build.timestamp).desc())
        )
        builds = session.exec(statement).fetchall()

        return {
            build.recipe_name: (build, build.rebuilds[-1] if build.rebuilds else None)
            for build in builds
        }


# Function to save the build, rebuild or recipe in the database
def save(build: Build | Rebuild | Recipe):
    with get_session() as session:
        session.add(build)
        session.commit()


# Function to query the database and return rebuild data
def get_rebuild_data() -> Sequence[Build]:
    with get_session() as session:
        # Subquery to get the latest build per platform
        latest_build_subquery = (
            select(Build, func.max(Build.timestamp).label("latest_timestamp"))
            .group_by(Build.platform_name)
            .group_by(Build.recipe_name)
            .order_by(col(Build.timestamp).desc())
        )

        # Main query to get the latest builds
        all_group_builds = session.exec(latest_build_subquery).all()
        latest_builds = [build for build, _ in all_group_builds]

        [build.rebuilds for build in latest_builds]
        return latest_builds


# Function to query the database and return recipe data
def get_recipe(url: str, path: str | Path, rev: str) -> Optional[RemoteRecipe]:
    path = str(path)
    with get_session() as session:
        # Subquery to get the latest build per platform
        recipe_query = (
            select(RemoteRecipe)
            .where(RemoteRecipe.url == url)
            .where(RemoteRecipe.path == path)
            .where(RemoteRecipe.rev == rev)
        )

        return session.exec(recipe_query).first()


def get_total_unique_recipes(session: Optional[SqlModelSession] = None) -> int:
    """Query to get the total number of unique recipes"""
    with get_session() if not session else session as session:
        return session.exec(select(func.count(distinct(RemoteRecipe.name)))).one()


@dataclass
class SuccessfulBuildsAndRebuilds:
    builds: int
    rebuilds: int


def get_total_successful_builds_and_rebuilds(
    before_time: datetime,
    after_time: Optional[datetime],
    session: Optional[SqlModelSession] = None,
) -> SuccessfulBuildsAndRebuilds:
    """Query to get the total number of successful builds and rebuilds before the given timestamp."""
    with get_session() if not session else session as session:
        # Subquery to find the latest build for each unique recipe_name before the given timestamp
        select_matching_builds = (
            select(
                Build.id,
            )
            .where(
                col(Build.timestamp) <= before_time,
                (col(Build.timestamp) > after_time)
                if after_time is not None
                else literal(True),
            )
            .group_by(Build.recipe_name)
        )
        subquery = select_matching_builds.subquery()
        # Query to get the total number of successful builds
        successful_builds_query = (
            select(func.count(col(Build.id)))
            .join(subquery, (col(Build.id) == subquery.c.id))
            .where(Build.state == BuildState.SUCCESS)
        )

        # Query to get the total number of successful rebuilds for the selected builds
        successful_rebuilds_query = select(func.count(col(Rebuild.id))).where(
            col(Rebuild.build_id).in_(select(subquery)),
            Rebuild.state == BuildState.SUCCESS,
        )

        # Execute the queries and count the results
        successful_builds_count = session.exec(successful_builds_query).one()
        successful_rebuilds_count = session.exec(successful_rebuilds_query).one()
        return SuccessfulBuildsAndRebuilds(
            successful_builds_count, successful_rebuilds_count
        )
