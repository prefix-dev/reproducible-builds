from datetime import datetime
from sqlmodel import Session
from repror.internals.db import (
    Build,
    BuildState,
    Rebuild,
    setup_local_db,
    get_total_successful_builds_and_rebuilds,
)

# Define a couple of timestamps
timestamp1 = datetime(2023, 1, 1, 12, 0, 0)
timestamp2 = datetime(2023, 6, 1, 12, 0, 0)


def seed_data(session: Session):
    # Sample Build and Rebuild data
    builds = [
        Build(
            id=1,
            recipe_name="Recipe1",
            state=BuildState.SUCCESS,
            build_tool_hash="hash1",
            recipe_hash="rhash1",
            platform_name="windows",
            platform_version="v1",
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
            build_tool_hash="hash2",
            recipe_hash="rhash2",
            platform_name="windows",
            platform_version="v2",
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
            build_tool_hash="hash3",
            recipe_hash="rhash3",
            platform_name="windows",
            platform_version="v3",
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
            build_tool_hash="hash4",
            recipe_hash="rhash4",
            platform_name="windows",
            platform_version="v4",
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
            build_tool_hash="hash4",
            recipe_hash="rhash4",
            platform_name="windows",
            platform_version="v4",
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
    session.commit()


def test_aggregation():
    sessionmaker = setup_local_db()
    with sessionmaker() as session:
        # Seed data
        seed_data(session)
        assert timestamp2 > timestamp1
        result = get_total_successful_builds_and_rebuilds(
            "windows", before_time=timestamp1, session=session
        )
        assert result.builds == 1
        assert result.rebuilds == 1
        assert result.total_builds == 1
        result = get_total_successful_builds_and_rebuilds(
            "windows", before_time=timestamp2, session=session
        )
        assert result.builds == 4
        assert result.rebuilds == 4
        assert result.total_builds == 5
