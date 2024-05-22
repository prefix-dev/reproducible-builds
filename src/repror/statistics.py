import datetime
import json
import sys


if __name__ == "__main__":
    platform_with_versions = sys.argv[1:]

    if "ubuntu_22.04_20.04" not in platform_with_versions:
        print(
            "ubuntu_22.04_20.04 platform is required ,for now, to calculate total statistics"
        )
        sys.exit(1)

    build_info_by_platform = {}
    rebuild_info_by_platform = {}

    total_build_info = {}
    total_rebuild_info = {}

    for platform_and_version in platform_with_versions:
        base_platform, from_version, to_version = platform_and_version.split("_")

        with open(
            f"build_info/{base_platform}_{from_version}_build_info.json", "r"
        ) as f:
            build_info_by_platform[base_platform] = json.load(f)

        with open(
            f"build_info/{base_platform}_{from_version}_{to_version}_rebuild_info.json",
            "r",
        ) as f:
            rebuild_info_by_platform[base_platform] = json.load(f)

        if base_platform == "ubuntu":
            total_build_info.update(build_info_by_platform["ubuntu"])
            total_rebuild_info.update(rebuild_info_by_platform["ubuntu"])

    # calculate entire statistics that will be used to render main table
    assert len(total_build_info) == len(total_rebuild_info)

    today_date = datetime.datetime.now().strftime("%Y-%m-%d")

    build_results_by_platform = {}

    for platform in build_info_by_platform:
        build_results_by_platform[platform] = {}
        for recipe_name, info in build_info_by_platform[platform].items():
            if not info:
                build_results_by_platform[platform][recipe_name] = False
                continue

            re_info = rebuild_info_by_platform[platform][recipe_name]

            if not re_info:
                build_results_by_platform[platform][recipe_name] = False
                continue

            build_results_by_platform[platform][recipe_name] = (
                info["pkg_hash"] == re_info["pkg_hash"]
            )

        with open(f"data/{platform}_packages_info_{today_date}.json", "w") as pkg_info:
            import pdb

            pdb.set_trace()
            json.dump(build_results_by_platform[platform], pkg_info)
