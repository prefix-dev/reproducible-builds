import datetime
import json
import sys



if __name__ == "__main__":

    platforms = sys.argv[1:]

    if "linux_linux" not in platforms:
        print("linux_linux platform is required , for now, to calculate total sum")
        sys.exit(1)

    build_info_by_platform = {}
    rebuild_info_by_platform = {}

    total_build_info = {}
    total_rebuild_info = {}


    for platform in platforms:
        build_platform, rebuild_platform = platform.split("_")
        
        with open(f"build_info/{build_platform}_build_info.json", "r") as f:
            build_info_by_platform[platform] = json.load(f)
        
        with open(f"build_info/{platform}_rebuild_info.json", "r") as f:
            rebuild_info_by_platform[platform] = json.load(f)

        if platform == "macos_macos":
            total_build_info.update(build_info_by_platform[platform])
            total_rebuild_info.update(rebuild_info_by_platform[platform])


    assert len(total_build_info) == len(total_rebuild_info)
    total_packages = len(total_build_info)

    build_results = {}

    for recipe_name, info in total_build_info.items():
        if not info:
            build_results[recipe_name] = False
            continue
        
        re_info = total_rebuild_info[recipe_name]

        if not re_info:
            build_results[recipe_name] = False
            continue

        build_results[recipe_name] = info["pkg_hash"] == re_info["pkg_hash"]

    
    
    reproducible = sum(1 for value in build_results.values() if value)
    not_reproducible = sum(1 for value in build_results.values() if not value)

    today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    with open(f"data/chart_data_{today_date}.txt", "w") as f:
        f.write(f"{total_packages} {reproducible} {not_reproducible}\n")

    with open(f"data/packages_info_{today_date}.json", "w") as pkg_info:
        json.dump(build_results, pkg_info)