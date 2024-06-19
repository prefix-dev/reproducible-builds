from datetime import datetime
from enum import Enum
import hashlib
import logging
from typing import Optional
from sqlalchemy import func, text
from typing import Sequence, TypeGuard
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import (
    Field,
    Relationship,
    SQLModel,
    and_,
    create_engine,
    or_,
    select,
    Session as SqlModelSession,
    col,
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
    if __engine_is_set(engine):
        SQLModel.metadata.create_all(engine)


def setup_engine(in_memory: bool = False):
    """Setup the sqlite engine."""
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
        __engine_is_set(engine)
        return func(*args, **kwargs)

    return wrapper


def __engine_is_set(engine) -> TypeGuard[Engine]:
    if not engine:
        raise RuntimeError("Engine is not set. Call setup_engine() first.")
    return engine is not None


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
def get_latest_builds(
    recipe_names_and_hash: list[tuple[str, str]],
    build_tool_hash: str,
    platform_name: str,
    platform_version: str,
) -> dict[str, Build]:
    with Session() as session:
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


@check_engine_is_set
def get_latest_build_with_rebuild(
    recipe_names_and_hash: list[tuple[str, str]],
    build_tool_hash: str,
    platform_name: str,
    platform_version: str,
) -> dict[str, tuple[Build, Optional[Rebuild]]]:
    with Session() as session:
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
        )

        # Main query to get the latest builds
        all_group_builds = session.exec(latest_build_subquery).all()
        latest_builds = [build for build, _ in all_group_builds]

        [build.rebuilds for build in latest_builds]
        return latest_builds
