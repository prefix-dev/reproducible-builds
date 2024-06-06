import hashlib
import platform
import pandas as pd
import sqlite3
from sqlite3 import Connection


# Function to compute the hash of the build tool version and recipe
def compute_hash(value: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(value.encode("utf-8"))
    return hasher.hexdigest()


# Function to initialize the SQLite database
def init_db(db_name="repro.db") -> Connection:
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Create build table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS build (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_name TEXT,
            state TEXT,
            build_tool_hash TEXT,
            recipe_hash TEXT,
            platform_name TEXT,
            platform_version TEXT,
            build_hash TEXT,
            build_loc TEXT,
            reason TEXT,
            timestamp TEXT
        )
    """)

    # Create rebuild table with a foreign key relationship to the build table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rebuild (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_name TEXT,
            build_id INTEGER,
            state TEXT,
            reason TEXT,
            hash TEXT,
            timestamp TEXT,
            FOREIGN KEY(build_id) REFERENCES build(id)
        )
    """)

    conn.commit()
    return conn


# Function to check if the hash exists in the database
def get_latest_build(
    conn: Connection,
    recipe_name,
    build_tool_hash,
    recipe_hash,
    platform_name,
    platform_version,
) -> dict:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM build WHERE recipe_name=? AND build_tool_hash=? AND recipe_hash=? AND platform_name=? AND platform_version=? ORDER BY timestamp desc",
        (recipe_name, build_tool_hash, recipe_hash, platform_name, platform_version),
    )
    return cursor.fetchone()


# Function to save the new build hash in the database
def save_build(
    conn: Connection, recipe_name, build_tool_hash, recipe_hash, build_hash, build_loc
):
    platform_name, platform_version = platform.system().lower(), platform.release()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO build (recipe_name, state, build_tool_hash, recipe_hash, platform_name, platform_version, build_hash, build_loc, timestamp)
        VALUES (?, "succes", ?, ?, ?, ?, ?, ?, unixepoch())
        RETURNING *
    """,
        (
            recipe_name,
            build_tool_hash,
            recipe_hash,
            platform_name,
            platform_version,
            build_hash,
            build_loc,
        ),
    )
    inserted = cursor.fetchall()
    conn.commit()
    return inserted


# Function to save the new build hash in the database
def save_failed_build(
    conn: Connection, recipe_name, build_tool_hash, recipe_hash, reason: str
):
    platform_name, platform_version = platform.system().lower(), platform.release()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO build (recipe_name, state, build_tool_hash, recipe_hash, platform_name, platform_version, reason, timestamp)
        VALUES (?, "fail", ?, ?, ?, ?, ?, unixepoch())
    """,
        (
            recipe_name,
            build_tool_hash,
            recipe_hash,
            platform_name,
            platform_version,
            reason,
        ),
    )
    conn.commit()


# Function to check if the hash exists in the database
def get_latest_rebuild(conn: Connection, build_id) -> dict:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM rebuild WHERE build_id=? ORDER BY timestamp desc", (build_id,)
    )
    return cursor.fetchone()


def save_rebuild(conn: Connection, recipe_name, build_id, hash):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO rebuild (recipe_name, build_id, state, hash, timestamp)
        VALUES (?, ?, "succes", ?, unixepoch())
        RETURNING *
    """,
        (recipe_name, build_id, hash),
    )
    inserted = cursor.fetchall()
    conn.commit()
    return inserted


def save_failed_rebuild(conn: Connection, recipe_name, build_id, reason):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO rebuild (recipe_name, build_id, state, reason, timestamp)
        VALUES (?, ?, "fail", ?, unixepoch())
        RETURNING *
    """,
        (recipe_name, build_id, reason),
    )
    inserted = cursor.fetchall()
    conn.commit()
    return inserted


# Function to query the database and return rebuild data
def get_rebuild_data():
    conn = init_db()
    query = """
    SELECT r.id, r.recipe_name, r.state, r.hash, r.reason, b.build_hash, r.timestamp
    FROM rebuild r
    JOIN build b ON r.build_id = b.id
    INNER JOIN (
        SELECT build_id, MAX(timestamp) as latest_timestamp
        FROM rebuild
        GROUP BY build_id
    ) latest_rebuild ON r.build_id = latest_rebuild.build_id AND r.timestamp = latest_rebuild.latest_timestamp
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df
