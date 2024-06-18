from datetime import datetime
from enum import Enum
import hashlib
import logging
from typing import Optional, Sequence, Tuple
from sqlalchemy import func, text
from sqlalchemy.orm import sessionmaker
from sqlmodel import (
    Field,
    Relationship,
    SQLModel,
    create_engine,
    select,
    Session as SqlModelSession,
    col
)


# Suppress SQLAlchemy INFO logs
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


# Function to compute the hash of the build tool version and recipe
def compute_hash(value: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(value.encode("utf-8"))
    return hasher.hexdigest()


class BuildState(str, Enum):
    SUCCESS = "success"
    FAIL = "fail"


engine = None
Session = sessionmaker(class_=SqlModelSession)


def create_db_and_tables():
    global engine
    if not engine:
        raise RuntimeError("Engine is not set. Call setup_engine() first.")
    SQLModel.metadata.create_all(engine)


def setup_engine(in_memory: bool = False):
    """Setup the sqlite engine."""
    print(f"Setting up engine with in_memory={in_memory}")
    global engine, Session
    if engine:
        return

    if in_memory:
        engine = create_engine("sqlite:///:memory:", echo=False)
    else:
        sqlite_file_name = "repro.db"
        sqlite_url = f"sqlite:///{sqlite_file_name}"
        engine = create_engine(sqlite_url, echo=False)

    Session.configure(bind=engine)
    create_db_and_tables()


# The decorator function
def check_engine_is_set(func):
    def wrapper(*args, **kwargs):
        global engine
        if not engine:
            raise RuntimeError("Engine is not set. Call setup_engine() first.")
        return func(*args, **kwargs)

    return wrapper


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


@check_engine_is_set
def get_latest_build(
    recipe_name: str,
    build_tool_hash: str,
    recipe_hash: str,
    platform_name: str,
    platform_version: str,
) -> Optional[Build]:
    with Session() as session:
        statement = (
            select(Build)
            .where(Build.recipe_name == recipe_name)
            .where(Build.build_tool_hash == build_tool_hash)
            .where(Build.recipe_hash == recipe_hash)
            .where(Build.platform_name == platform_name)
            .where(Build.platform_version == platform_version)
            .order_by(col(Build.timestamp).desc())
            .limit(1)
        )
        build = session.exec(statement).first()
        return build


@check_engine_is_set
def get_latest_build_with_rebuild(
    recipe_name: str,
    build_tool_hash: str,
    recipe_hash: str,
    platform_name: str,
    platform_version: str,
) -> Tuple[Build, Optional[Rebuild]]:
    with Session() as session:
        statement = (
            select(Build)
            .where(Build.recipe_name == recipe_name)
            .where(Build.build_tool_hash == build_tool_hash)
            .where(Build.recipe_hash == recipe_hash)
            .where(Build.platform_name == platform_name)
            .where(Build.platform_version == platform_version)
            .order_by(col(Build.timestamp).desc())
            .limit(1)
        )
        result = session.execute(statement)
        build = result.scalars().first()
        if not build:
            raise ValueError("No build found")
        rebuild = build.rebuilds[-1] if build and build.rebuilds else None

        return build, rebuild


@check_engine_is_set
# Function to save the new build or rebuild in the database
def save(build: Build | Rebuild):
    with Session() as session:
        session.add(build)
        session.commit()


@check_engine_is_set
# Function to query the database and return rebuild data
def get_rebuild_data() -> Sequence[Build]:
    with Session() as session:
        # Subquery to get the latest build per platform
        latest_build_subquery = (
            select(Build, func.max(Build.timestamp).label("latest_timestamp"))
            .group_by(Build.platform_name)
            .group_by(Build.recipe_name)
            .order_by(col(Build.timestamp).desc())
            .limit(1)
        )

        # Main query to get the latest builds
        all_group_builds = session.exec(latest_build_subquery).all()
        latest_builds = [build for build, _ in all_group_builds]

        [build.rebuilds for build in latest_builds]
        return latest_builds
