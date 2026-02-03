from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import logging
import os
from pathlib import Path
import tempfile
from typing import Generator, Literal as Lit, Optional
from pydantic import BaseModel
from sqlalchemy import func, text
from typing import Sequence
from sqlalchemy.orm import sessionmaker, scoped_session
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
)

from repror.internals.recipe import clone_remote_recipe
from .print import print


def _print_status(msg: str) -> None:
    """Print status message to stderr to avoid interfering with stdout capture."""
    import sys
    from rich.console import Console

    console = Console(file=sys.stderr)
    console.print(msg)


# Suppress SQLAlchemy INFO logs
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

engine = None
# Create a session class that binds to SQLModelSession
session_factory = sessionmaker(class_=SqlModelSession, expire_on_commit=False)
__Session = scoped_session(session_factory)

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
    global engine
    assert engine  # This should not fail
    SQLModel.metadata.create_all(engine)


def setup_engine(in_memory: bool = False):
    """Setup the sqlite engine."""
    _print_status(f"Setting up engine with in_memory={in_memory}")
    global engine, __Session
    if engine:
        # Engine is already set, skip initialization
        _print_status("Engine already set, skipping initialization")
        return

    if in_memory:
        engine = create_engine("sqlite:///:memory:")
    else:
        # Get the name of the database from an environment variable
        # or use the default name which is a local database
        sqlite_file_name = os.getenv("REPRO_DB_NAME", "repro.local.db")
        # Do a manual check for safety
        if sqlite_file_name == PROD_DB:
            _print_status("[dim yellow]Running on production[/dim yellow]")
        else:
            _print_status(f"[dim green]Running on {sqlite_file_name}[/dim green]")

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


def get_session() -> SqlModelSession:
    """Get a new session."""
    global engine
    assert engine
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


class V1Rebuild(SQLModel, table=True):
    """Database model for V1 package rebuild attempts from conda-forge."""

    __tablename__ = "v1_rebuild"

    id: Optional[int] = Field(default=None, primary_key=True)
    package_name: str
    version: str
    # Conda subdir (e.g., linux-64, noarch, osx-arm64)
    subdir: Optional[str] = None
    # Build string (e.g., py_0, h123abc_0)
    build_string: Optional[str] = None
    original_url: str
    original_hash: str
    rebuild_hash: Optional[str] = None
    state: BuildState
    reason: Optional[str] = None
    platform_name: str
    platform_version: str
    # The rattler-build version used for rebuilding
    build_tool_hash: str
    # Original build tool info extracted from the package
    original_build_tool: Optional[str] = None  # "conda-build" or "rattler-build"
    original_build_tool_version: Optional[str] = None
    timestamp: Optional[datetime] = Field(
        default=None,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )
    actions_url: Optional[str] = None

    @property
    def is_reproducible(self) -> bool:
        return (
            self.state == BuildState.SUCCESS
            and self.rebuild_hash is not None
            and self.original_hash == self.rebuild_hash
        )

    @property
    def was_built_with_rattler(self) -> bool:
        return self.original_build_tool == "rattler-build"


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


# Function to query the database and return latest rebuild data
def get_rebuild_data(
    recipe_names: Optional[list[str]] = None,
    platform: Optional[str] = None,
) -> Sequence[Build]:
    with get_session() as session:
        # Subquery to get the latest build per platform
        latest_build_subquery = (
            select(Build, func.max(Build.timestamp).label("latest_timestamp"))
            .group_by(Build.platform_name)
            .group_by(Build.recipe_name)
            .order_by(col(Build.timestamp).desc())
        )
        if platform:
            latest_build_subquery = latest_build_subquery.where(
                Build.platform_name == platform
            )

        if recipe_names:
            latest_build_subquery = latest_build_subquery.where(
                or_(col(Build.recipe_name).in_(recipe_names))
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
    with get_session() as session:
        return session.exec(select(func.count(distinct(RemoteRecipe.name)))).one()


@dataclass
class SuccessfulBuildsAndRebuilds:
    builds: int
    rebuilds: int
    total_builds: int


def get_total_successful_builds_and_rebuilds(
    platform_name: Lit["linux", "darwin", "windows"] | str,
    before_time: datetime,
) -> SuccessfulBuildsAndRebuilds:
    """Query to get the total number of successful builds and rebuilds before the given timestamp."""
    with get_session() as session:
        # Subquery to find the latest build for each unique recipe_name before the given timestamp
        select_matching_builds = (
            select(
                Build.id,
            )
            .where(
                col(Build.platform_name) == platform_name,
                col(Build.timestamp) <= before_time,
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

        total_builds_query = select(func.count(col(Build.id))).join(
            subquery, (col(Build.id) == subquery.c.id)
        )

        # Execute the queries and count the results
        successful_builds_count = session.exec(successful_builds_query).one()
        successful_rebuilds_count = session.exec(successful_rebuilds_query).one()
        total_builds: int = session.exec(total_builds_query).one()
        return SuccessfulBuildsAndRebuilds(
            successful_builds_count,
            successful_rebuilds_count,
            total_builds=total_builds,
        )


@dataclass
class V1RebuildStats:
    """Statistics for V1 rebuilds."""

    total: int
    successful: int
    reproducible: int
    failed: int

    @property
    def success_rate(self) -> float:
        return (self.successful / self.total * 100) if self.total > 0 else 0

    @property
    def reproducibility_rate(self) -> float:
        return (self.reproducible / self.successful * 100) if self.successful > 0 else 0


def get_v1_rebuild_data(
    platform: Optional[str] = None,
) -> Sequence[V1Rebuild]:
    """Get all V1 rebuild records, optionally filtered by platform."""
    with get_session() as session:
        query = select(V1Rebuild).order_by(col(V1Rebuild.timestamp).desc())
        if platform:
            query = query.where(V1Rebuild.platform_name == platform)
        return session.exec(query).all()


def get_v1_rebuild_stats(platform: Optional[str] = None) -> V1RebuildStats:
    """Get statistics for V1 rebuilds."""
    with get_session() as session:
        base_query = select(func.count(V1Rebuild.id))
        if platform:
            base_query = base_query.where(V1Rebuild.platform_name == platform)

        total = session.exec(base_query).one()

        successful_query = base_query.where(V1Rebuild.state == BuildState.SUCCESS)
        successful = session.exec(successful_query).one()

        reproducible_query = base_query.where(
            V1Rebuild.state == BuildState.SUCCESS,
            V1Rebuild.original_hash == V1Rebuild.rebuild_hash,
        )
        reproducible = session.exec(reproducible_query).one()

        failed = total - successful

        return V1RebuildStats(
            total=total,
            successful=successful,
            reproducible=reproducible,
            failed=failed,
        )
