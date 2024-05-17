import datetime
import glob
import os
import json
import conf
from pathlib import Path
import subprocess
import hashlib
import shutil
import tempfile
from repror.build import build_conda_recipe, rebuild_conda_package, setup_rattler_build

from repror.git import checkout_branch_or_commit, clone_repo
from util import calculate_hash, find_conda_build, get_recipe_name, move_file


if __name__ == "__main__":
    config = conf.load_config()

    with tempfile.TemporaryDirectory() as tmp_dir:

        rattler_clone_dir = Path(tmp_dir) / "rattler-clone"
        rattler_config = config["rattler-build"]

        setup_rattler_build(rattler_config, rattler_clone_dir)
            
        build_dir = Path(tmp_dir) / "build_outputs"
        build_dir.mkdir(exist_ok=True)

        cloned_prefix_dir = Path(tmp_dir) / "cloned"

        build_results = {}

        for repo in config.get("repositories", []):
            repo_url = repo["url"]
            ref = repo.get("branch") or repo.get("commit")
            clone_dir = cloned_prefix_dir.joinpath(
                repo_url.split("/")[-1].replace(".git", "")
            )

            if clone_dir.exists():
                shutil.rmtree(clone_dir)

            print(f"Cloning repository: {repo_url}")

            clone_repo(repo_url, clone_dir)

            if ref:
                print(f"Checking out {ref}")
                checkout_branch_or_commit(clone_dir, ref)

            for recipe in repo["recipes"]:
                recipe_path = clone_dir / recipe["path"]
                recipe_name = recipe_path.name

                print(f"Building recipe: {recipe_name}")

                # First build
                first_build_dir = build_dir / f"{recipe_name}_first"
                first_build_dir.mkdir(parents=True, exist_ok=True)

                try:
                    build_conda_recipe(recipe_path, first_build_dir)
                except subprocess.CalledProcessError:
                    # something went wrong with building it
                    # for now we record it as not rebuildable
                    # and skip to next recipe
                    build_results[str(recipe_path)] = False
                    continue

                # let's record first hash
                conda_file = find_conda_build(first_build_dir)
                print(conda_file)
                first_build_hash = calculate_hash(conda_file)

                # let's move the build
                rebuild_directory = build_dir / f"{recipe_name}_rebuild"
                rebuild_file_loc = move_file(conda_file, rebuild_directory)

                # let's rebuild it
                try:
                    rebuild_conda_package(rebuild_file_loc, first_build_dir)
                except subprocess.CalledProcessError:
                    # something went wrong with building it
                    # for now we record it as not rebuildable
                    # and skip to next recipe
                    build_results[str(recipe_path)] = False
                    continue

                # let's record rebuild hash
                re_conda_file = find_conda_build(first_build_dir)
                re_build_hash = calculate_hash(re_conda_file)

                if first_build_hash == re_build_hash:
                    build_results[str(recipe_path)] = True
                    print("they are the same!")
                else:
                    print("they are not the same!")
                    build_results[str(recipe_path)] = False

        for local in config.get("local", []):
            recipe_path = Path(local["path"])
            recipe_name = recipe_path.name
            package_name = get_recipe_name(recipe_path)
            print(f"Building recipe: {recipe_name}")

            # First build
            first_build_dir = build_dir / f"{recipe_name}_first"
            first_build_dir.mkdir(parents=True, exist_ok=True)
            try:
                build_conda_recipe(recipe_path, first_build_dir)
            except subprocess.CalledProcessError:
                # something went wrong with building it
                # for now we record it as not rebuildable
                # and skip to next recipe
                build_results[str(recipe_path)] = False
                continue

            # let's record first hash
            conda_file = find_conda_build(first_build_dir)
            print(conda_file)
            first_build_hash = calculate_hash(conda_file)

            # let's move the build
            rebuild_directory = build_dir / f"{recipe_name}_rebuild"
            rebuild_file_loc = move_file(conda_file, rebuild_directory)

            # let's rebuild it
            try:
                rebuild_conda_package(rebuild_file_loc, first_build_dir)
            except subprocess.CalledProcessError:
                # something went wrong with building it
                # for now we record it as not rebuildable
                # and skip to next recipe
                build_results[str(recipe_path)] = False
                continue

            # let's record rebuild hash
            re_conda_file = find_conda_build(first_build_dir)
            print(re_conda_file)
            re_build_hash = calculate_hash(re_conda_file)

            if first_build_hash == re_build_hash:
                print("they are the same!")
                build_results[str(recipe_path)] = True

            else:
                print("they are not the same!")
                build_results[str(recipe_path)] = False

    total_packages = len(build_results)
    reproducible = sum(value for value in build_results.values() if value)
    not_reproducible = sum(value for value in build_results.values() if not value)

    today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    with open(f"data/chart_data_{today_date}.txt", "w") as f:
        f.write(f"{total_packages} {reproducible} {not_reproducible}\n")

    with open(f"data/packages_info_{today_date}.json", "w") as pkg_info:
        json.dump(build_results, pkg_info)
