from datetime import datetime
from enum import StrEnum
import hashlib
from typing import Optional, Tuple
from sqlalchemy import text
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select


# Function to compute the hash of the build tool version and recipe
def compute_hash(value: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(value.encode("utf-8"))
    return hasher.hexdigest()


class BuildState(StrEnum):
    SUCCESS = "success"
    FAIL = "fail"


# DATABASE = 'repro.db'

# Defer initialization of the database until the script is executed from the
# command-line.
sqlite_file_name = "repro.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)


class Build(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    recipe_name: str
    state: BuildState
    build_tool_hash: str
    recipe_hash: str
    platform_name: str
    platform_version: str
    build_hash: Optional[str]
    build_loc: Optional[str]
    reason: Optional[str]
    timestamp: datetime = Field(
        default=None,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
        },
    )
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

    build: Build = Relationship(back_populates="rebuilds")


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


create_db_and_tables()


def dummy_data():
    build1 = Build(
        recipe_name="boltons",
        state=BuildState.SUCCESS,
        build_tool_hash=compute_hash("23.0.0"),
        recipe_hash=compute_hash("h4616a5c_0"),
        platform_name="darwin",
        platform_version="22.5.0",
        build_hash=compute_hash(
            "f370cf84e9ff55efdaa0bd7ea2b65ed2449ab5f258a8797412aaffd952776421"
        ),
        build_loc="artifacts/boltons-23.0.0-pyh4616a5c_0.conda",
        reason=None,
    )

    rebuild = Rebuild(
        # build_id=build1.id,
        state=BuildState.SUCCESS,
        reason=None,
        rebuild_hash=compute_hash(
            "f370cf84e9ff55efdaa0bd7ea2b65ed2449ab5f258a8797412aaffd952776421"
        ),
        build=build1,
    )

    with Session(engine) as session:
        session.add(build1)
        session.add(rebuild)
        session.commit()


# # Function to initialize the SQLite database
# def init_db(db_name="repro.db") -> Connection:
#     conn = sqlite3.connect(db_name)
#     cursor = conn.cursor()

#     # Create build table
#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS build (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             recipe_name TEXT,
#             state TEXT,
#             build_tool_hash TEXT,
#             recipe_hash TEXT,
#             platform_name TEXT,
#             platform_version TEXT,
#             build_hash TEXT,
#             build_loc TEXT,
#             reason TEXT,
#             timestamp TEXT
#         )
#     """)

#     # Create rebuild table with a foreign key relationship to the build table
#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS rebuild (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             recipe_name TEXT,
#             build_id INTEGER,
#             state TEXT,
#             reason TEXT,
#             hash TEXT,
#             timestamp TEXT,
#             FOREIGN KEY(build_id) REFERENCES build(id)
#         )
#     """)

#     conn.commit()
#     return conn


# Function to check if the hash exists in the database
def get_latest_build(
    recipe_name: str,
    build_tool_hash: str,
    recipe_hash: str,
    platform_name: str,
    platform_version: str,
) -> Build:
    with Session(engine) as session:
        statement = (
            select(Build)
            .where(Build.recipe_name == recipe_name)
            .where(Build.build_tool_hash == build_tool_hash)
            .where(Build.recipe_hash == recipe_hash)
            .where(Build.platform_name == platform_name)
            .where(Build.platform_version == platform_version)
            .order_by(Build.timestamp.desc())
            .limit(1)
        )
        build = session.exec(statement).first()
        return build


# Function to check if the hash exists in the database
def get_latest_build_with_rebuild(
    recipe_name: str,
    build_tool_hash: str,
    recipe_hash: str,
    platform_name: str,
    platform_version: str,
) -> Tuple[Build, Optional[Rebuild]]:
    with Session(engine) as session:
        statement = (
            select(Build)
            .where(Build.recipe_name == recipe_name)
            .where(Build.build_tool_hash == build_tool_hash)
            .where(Build.recipe_hash == recipe_hash)
            .where(Build.platform_name == platform_name)
            .where(Build.platform_version == platform_version)
            .order_by(Build.timestamp.desc())
            .limit(1)
        )
        build = session.exec(statement).first()
        rebuild = build.rebuilds[-1] if build.rebuilds else None

        return build, rebuild


# Function to save the new build or rebuild in the database
def save(build: Build | Rebuild):
    with Session(engine) as session:
        session.add(build)
        session.commit()


# Function to query the database and return rebuild data
def get_rebuild_data() -> list[Build]:
    with Session(engine) as session:
        # Subquery to get the latest build per platform
        latest_build_subquery = (
            select(
                Build,
                # func.max(Build.timestamp).label("latest_timestamp")
            )
            .group_by(Build.platform_name)
            .group_by(Build.recipe_name)
            .order_by(Build.timestamp.desc())
        )

        # Main query to get the latest builds
        latest_builds = session.exec(latest_build_subquery).all()

        [build.rebuilds for build in latest_builds]
        return latest_builds
