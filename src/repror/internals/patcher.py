import json
from repror.cli.rewrite_readme import find_infos


import sqlite3


# Load the patch data
def patch(patch_data):
    # Connect to the SQLite database
    conn = sqlite3.connect("repro.db")
    cursor = conn.cursor()

    # Insert build data without build_id
    build_data = patch_data["build"][1:]
    cursor.execute(
        """
        INSERT INTO build (recipe_name, state, build_tool_hash, recipe_hash, platform_name, platform_version, build_hash, build_loc, reason, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        build_data,
    )
    conn.commit()

    # Query the inserted build_id
    cursor.execute("SELECT last_insert_rowid()")
    build_id = cursor.fetchone()[0]

    # Update the rebuild table with the correct build_id
    rebuild_data = patch_data["rebuild"][1:]
    rebuild_data[1] = build_id
    cursor.execute(
        """
        INSERT INTO rebuild (recipe_name, build_id, state, reason, hash, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        rebuild_data,
    )
    conn.commit()

    # Query the inserted data from the build table
    cursor.execute("SELECT * FROM build WHERE id=?", (build_id,))
    result = cursor.fetchone()
    print(result)

    # Close the connection
    conn.close()


def merge_patches(build_info_dir: str = "build_info") -> dict:
    build_infos = find_infos(build_info_dir, "info")

    for build_file in build_infos:
        with open(build_file, "r") as f:
            patch_data = json.load(f)
            patch(patch_data)
