import datetime
import json



if __name__ == "__main__":

    with open("build_info/build_info.json", "r") as f:
        build_info = json.load(f)
    
    with open("build_info/rebuild_info.json", "r") as f:
        rebuild_info = json.load(f)



    assert len(build_info) == len(rebuild_info)
    total_packages = len(build_info)

    build_results = {}

    for recipe_name, info in build_info.items():
        if not info:
            build_results[recipe_name] = False
            continue
        
        re_info = rebuild_info[recipe_name]

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