import datetime
import glob
import os
import subprocess
import hashlib
import shutil
import tempfile

recipes = ['recipes/recipe.yaml']
total_packages = 0
reproducible = 0
not_reproducible = 0


with tempfile.TemporaryDirectory() as tmp_dir:
    for recipe in recipes:
        total_packages += 1
        folder_path = f'{tmp_dir}/output'
        subprocess.run(['rattler-build', 'build', "-r", recipe, "--output-dir", folder_path])
        
        destination_directory = f'{tmp_dir}/rebuild_folder'
        conda_file = glob.glob(folder_path + '/**/*.conda', recursive=True)[0]
        filename = os.path.basename(conda_file)
        print(conda_file)


        with open(conda_file, "rb") as f:
            # Read the entire file
            data = f.read()
            # Calculate the SHA-256 hash
            build_hash = hashlib.sha256(data).hexdigest()



        os.makedirs(destination_directory, exist_ok=True)

        shutil.move(conda_file, f"{destination_directory}/{filename}")

        subprocess.run(['rattler-build', 'rebuild', "--package-file", f"{destination_directory}/{filename}", "--output-dir", folder_path])

        rebuilded_conda_file = glob.glob(folder_path + '/**/*.conda', recursive=True)[0]
        rebuilded_filename = os.path.basename(conda_file)

        with open(rebuilded_conda_file, "rb") as f:
            # Read the entire file
            data = f.read()
            # Calculate the SHA-256 hash
            re_build_hash = hashlib.sha256(data).hexdigest()

        
        if build_hash == re_build_hash:
            reproducible += 1
        else:
            not_reproducible += 1


today_date = datetime.datetime.now().strftime("%Y-%m-%d")
with open(f'data/chart_data_{today_date}.txt', 'a') as f:
    f.write(f'{total_packages} {reproducible} {not_reproducible}\n')
    
