# Are we reproducible yet?

![License][license-badge]
[![Project Chat][chat-badge]][chat-url]

[license-badge]: https://img.shields.io/badge/license-BSD--3--Clause-blue?style=flat-square
[chat-badge]: https://img.shields.io/discord/1082332781146800168.svg?label=&logo=discord&logoColor=ffffff&color=7389D8&labelColor=6A7EC2&style=flat-square
[chat-url]: https://discord.gg/kKV8ZxyzY4

# 🏁🏁 Build Status 🏁🏁
You can view the current build status for the different packages [here](https://prefix-dev.github.io/reproducible-builds/).

## Introduction
This project aims to see if we can create reproducible builds for a variety of software packages.
The project is based on definitions of the [Reproducible Builds](https://reproducible-builds.org/) project.
It uses The [Rattler Build](https://github.com/prefix-dev/rattler-build) project, to build [Conda](https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html) packages.
This repository has CI setup to build packages for the latests: windows, linux and osx platforms.
It then tries to vary the build environment to see if the build is reproducible.

## What is a reproducible build?
We want to create a build process that reproduces bit-for-bit identical packages when run from the same build environment, while allowing for minor variations in the build environment. Mainly to test said reproducibility.

## How do we validate reproducibility?
We validate that rattler-build is a reproducible build tool by ensuring that it can recreate identical packages given the same recipe and build environment. We verify this by comparing the SHA256 hash of the original build and the rebuild. If the hashes differ, we inspect the packages with `diffoscope` to identify the differences. Common issues affecting reproducibility include unsorted files, differing archive timestamps, and reset script permissions during the archiving step.

### Platform variations
The following variations are tested (per platform):
* **Linux**: Locale, timezone
* **OSX**: Locale, timezone
* **Windows**: None yet (TODO). Open to suggestions!

This is similar to what other projects in the [Reproducible Builds](https://reproducible-builds.org/) project do, but for Conda packages.
If you have any more suggestions for variations, please let us know!

## Getting Started 🚀
This project uses [pixi](https://github.com/prefix-dev/pixi) for project management.

### Prerequisite
Complete the following steps only once:

1. Install Pixi by following the instructions on https://prefix.dev/
2. For building of local `rattler-build` versions install [rust](https://rustup.rs/). We might include this in the pixi configuration in the future.
3. Clone the repository and navigate to the root directory:
    ```bash
    git clone https://github.com/prefix-dev/reproducible-builds # or ssh
    cd reproducible-builds
    ```
Ensure that all subsequent commands are executed in the project's root directory. When running the commands, the necessary environment will be set up automatically.

## Quick Start
To see if the project is setup correctly, run the following command:

```bash
# Build/Rebuild the boltons package
pixi r reproduce boltons
# .. rattler-build output ..
# ...🕒🕒🕒🕒🕒
# ... a while later ...
Done: 'boltons'
Verifying if rebuilds are reproducible...
                                       Build Info
┏━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Platform ┃ Version ┃ Rattler Build Hash                                               ┃
┡━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ darwin   │ 22.3.0  │ 1c47eafc2fbd6bc6d8d629b40c4d2950e7de35a3f26712dd5d4eeba26dd33aba │
└──────────┴─────────┴──────────────────────────────────────────────────────────────────┘
 Is the Recipe Repro?
┏━━━━━━━━━┳━━━━━━━━━━━┓
┃ Name    ┃ Is Repro? ┃
┡━━━━━━━━━╇━━━━━━━━━━━┩
│ boltons │ Yes       │
└─────────┴───────────┘
# We have now successfully built the boltons package and verified that it is reproducible.
```
Once this is done we can generate the html page to view the results, similar as to what is shown at [Results](https://prefix-dev.github.io/reproducible-builds/). To do this run the following command:

```bash
pixi r serve-html
✨ Pixi task (serve-html in html): livereload -d ./docs.local/
Serving on http://127.0.0.1:35729
```

You can now view the html page at http://127.0.1.1:35729. Changes to this page will automatically be picked up.

### Configuration
#### Config.yaml (what recipes to build) ⚙️
The `config.yaml` file contains the configuration for the project. You can add `remote` or `local` recipes, that are local to the project or remote repositories.
The config also contains the rattler-build version that its using, this way we can depend on unreleased versions. This project automatically sets this up for you.

#### SQLite Database (stores the build information) 📕
This project uses a Sqlite database to store the build information. The database is created automatically when the project is setup.
When running locally a local version of the database is created, this will ensure that you have a clean database to work with.
You can also use the `--in-memory-sql` flag to use an in-memory database, which is useful for testing.
E.g `pixi run repror --in-memory-sql build-recipe boltons`, this will build the boltons recipe in an in-memory database.

## Running locally 🏃‍♂️
This project exposes a Python CLI called `repror` to interact with the project. We also re-expose the CLI using pixi tasks.

### Using the pixi tasks 📋
Currently the following tasks are available for **building/reproducing**:
* `reproduce` builds and rebuilds a recipe for the current platform.
* `build-recipe <name>` to build a recipe.
* `build-recipe-skip` same as above but uses the `rattler-build` defined in the `pixi.toml`.
* `rebuild-recipe` rebuilds the recipe. Requires that it has been built once.
* `rebuild-recipe-skip` same as above but uses the `rattler-build` defined in the `pixi.toml`.
* `check` checks the database which recipes are reproducible.
Note, that you can use the `--force` flag to force a rebuild of the recipe.

#### Recipe conversion
There is also the following task for **converting recipes**:
* `convert-recipe` that converts a `conda-build` `meta.yaml` to a `rattler-build` `recipe.yaml`.

#### HTML generation
A static html page is generated with the results of the builds, this can be found in the `docs` folder.
to **create the html** page run the following task:
* `generate-html` to generate the html page, from your local database.
* `serve-html` to serve the html page. This will generate the html page first.
There are additional `-prod` tasks that work on the production data, e.g. `generate-html-prod`.

#### Testing
Testing the repository can be done by running the following task:
* `test` to run the pytests.

### Using the Python CLI directly 🐍
Sometimes, the tasks do not cover the full functionality of the CLI. In such cases, you can use the CLI directly. Make sure that the environment has been installed using `pixi install` or by running one of the tasks.
To use the CLI directly, run the following command:

```bash
Use `pixi r repror`
```

This should give you some `--help` on how to use the CLI.

## Running on CI 🌎
The project is setup to run on CI, and will build the recipes for the different platforms.

### Caching strategy
If the recipe has been built and reproduced it will **only** be built again if the `rattler-build` version or the recipe has been changed.
After a successful build, a new `index.html` will be generated.

### CI Steps
The CI has the following stages:
* `setup-rattler-build` to install the `rattler-build` version. Can use a cached version, if it was built before.
* `generate-recipes` generates the build matrix recipe/platform, so we know what recipes to build.
* `build-and-rebuld-recipe` builds and rebuilds the recipes per platform. This step is cached.
* `patch-db` because the database is a SQLite database we cannot update per job, so we create metadata files that are `patched` into the database, the database is pushed to `main`, this step also generates the `index.html` file.


## Contributing 🤝
Easiest way to contribute is to create a PR with a new recipe, by adding it to the `config.yaml` file, either through a `remote` or a `local` source. This way we can check
the reproducibility for this specific recipe. This should also help us find `rattler-build` changes that we can make to prodoce more reproducible builds.

You can also help us by debugging packages that fail in build or reproducibility, we've tried to make it easy to run the project locally. We know how annoying it can be to wait for CI. Any improvements here are welcome as well!

## Licensing Information

This repository contains modified recipe scripts derived from the conda-forge project. As these scripts are based on work from conda-forge, they are subject to the conda-forge BSD-3-Clause license. You can find the license details in the `LICENSE_PACKAGES.txt` file in this repository.

By using or redistributing the recipes or packages from this repository, you agree to adhere to the terms of the BSD-3-Clause license provided by conda-forge.
