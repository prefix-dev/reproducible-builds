from repror.cli.utils import platform_name
from repror.internals.db import (
    get_total_successful_builds_and_rebuilds,
)


# Use the db_access fic
def test_aggregation(db_access):
    assert db_access.build_time_2 > db_access.build_time_1
    result = get_total_successful_builds_and_rebuilds(
        platform_name=platform_name(), before_time=db_access.build_time_1
    )
    assert result.builds == 1
    assert result.rebuilds == 1
    assert result.total_builds == 1
    result = get_total_successful_builds_and_rebuilds(
        platform_name=platform_name(), before_time=db_access.build_time_2
    )
    assert result.builds == 4
    assert result.rebuilds == 4
    assert result.total_builds == 5
