"""
V1 Recipe Sampler Module

This module fetches V1 recipe data from the are-we-recipe-v1-yet repository,
samples a random subset of packages, and attempts to rebuild existing
conda-forge packages using rattler-build rebuild.
"""

import json
import logging
import platform as plat
import random
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import tomllib
import typer
from urllib.request import urlopen, Request
from urllib.error import URLError

from repror.internals.db import (
    BuildState,
    V1Rebuild,
    save,
)
from repror.internals.patcher import save_v1_patch
from repror.internals.commands import (
    calculate_hash,
    find_conda_file,
    run_streaming_command,
    StreamingCmdOutput,
)
from repror.internals.rattler_build import get_rattler_build, rattler_build_hash
from repror.internals.print import print
from .utils import platform_name, platform_version

logger = logging.getLogger(__name__)

# URL for the feedstock-stats.toml file
FEEDSTOCK_STATS_URL = "https://raw.githubusercontent.com/tdejager/are-we-recipe-v1-yet/main/feedstock-stats.toml"

# Conda-forge base URL
CONDA_FORGE_BASE = "https://conda.anaconda.org/conda-forge"


def get_subdir() -> str:
    """Get the conda subdir for the current platform."""
    system = plat.system().lower()
    machine = plat.machine().lower()

    if system == "darwin":
        if machine == "arm64":
            return "osx-arm64"
        return "osx-64"
    elif system == "linux":
        if machine == "aarch64":
            return "linux-aarch64"
        return "linux-64"
    elif system == "windows":
        return "win-64"
    else:
        return "linux-64"


@dataclass
class FeedstockStats:
    """Statistics from the are-we-recipe-v1-yet repository."""

    total_feedstocks: int
    recipe_v1_count: int
    meta_yaml_count: int
    unknown_count: int
    last_updated: str
    v1_packages: list[str] = field(default_factory=list)


@dataclass
class PackageInfo:
    """Information about a conda package."""

    name: str
    version: str
    build: str
    build_number: int
    subdir: str
    filename: str
    url: str
    sha256: str
    size: int


@dataclass
class V1RebuildResult:
    """Result of rebuilding a V1 package from conda-forge."""

    package_name: str
    version: str
    original_url: str
    download_success: bool
    rebuild_success: bool
    reproducible: bool
    original_hash: Optional[str] = None
    rebuild_hash: Optional[str] = None
    error_message: Optional[str] = None


def fetch_feedstock_stats(url: str = FEEDSTOCK_STATS_URL) -> FeedstockStats:
    """Fetch and parse the feedstock-stats.toml file."""
    print(f"[dim]Fetching feedstock stats from {url}[/dim]")

    try:
        req = Request(url, headers={"User-Agent": "repror/1.0"})
        with urlopen(req, timeout=60) as response:
            content = response.read()
    except URLError as e:
        raise RuntimeError(f"Failed to fetch feedstock stats: {e}") from e

    data = tomllib.loads(content.decode("utf-8"))

    # Extract V1 packages from feedstock_states
    v1_packages = []
    feedstock_states = data.get("feedstock_states", {})

    for feedstock_name, state in feedstock_states.items():
        if state.get("recipe_type") == "recipe_v1":
            # Remove the "-feedstock" suffix to get package name
            package_name = feedstock_name.replace("-feedstock", "")
            v1_packages.append(package_name)

    stats = FeedstockStats(
        total_feedstocks=data.get("total_feedstocks", 0),
        recipe_v1_count=data.get("recipe_v1_count", 0),
        meta_yaml_count=data.get("meta_yaml_count", 0),
        unknown_count=data.get("unknown_count", 0),
        last_updated=data.get("last_updated", ""),
        v1_packages=v1_packages,
    )

    print(f"[green]Found {len(v1_packages)} V1 recipe packages[/green]")
    return stats


def fetch_repodata(subdir: str) -> dict:
    """Fetch the repodata.json for a given subdir."""
    # Use repodata.json (not current_repodata.json) for more complete data
    url = f"{CONDA_FORGE_BASE}/{subdir}/repodata.json"
    print(f"[dim]Fetching repodata from {url}[/dim]")

    try:
        req = Request(url, headers={"User-Agent": "repror/1.0"})
        with urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except URLError as e:
        raise RuntimeError(f"Failed to fetch repodata: {e}") from e


def find_package_in_repodata(
    package_name: str, repodata: dict, subdir: str
) -> Optional[PackageInfo]:
    """Find the latest version of a package in the repodata."""
    packages = repodata.get("packages.conda", {})

    # Find all matching packages (prefer .conda over .tar.bz2)
    matching = []
    for filename, info in packages.items():
        if info.get("name") == package_name:
            matching.append((filename, info))

    if not matching:
        # Try packages (tar.bz2)
        packages_tar = repodata.get("packages", {})
        for filename, info in packages_tar.items():
            if info.get("name") == package_name:
                matching.append((filename, info))

    if not matching:
        return None

    # Sort by build_number and version to get the latest
    def sort_key(item):
        filename, info = item
        return (info.get("version", "0"), info.get("build_number", 0))

    matching.sort(key=sort_key, reverse=True)

    filename, info = matching[0]
    url = f"{CONDA_FORGE_BASE}/{subdir}/{filename}"

    return PackageInfo(
        name=info["name"],
        version=info["version"],
        build=info.get("build", ""),
        build_number=info.get("build_number", 0),
        subdir=subdir,
        filename=filename,
        url=url,
        sha256=info.get("sha256", ""),
        size=info.get("size", 0),
    )


def download_package(pkg_info: PackageInfo, dest_dir: Path) -> Optional[Path]:
    """Download a package from conda-forge."""
    dest_file = dest_dir / pkg_info.filename
    print(f"[dim]Downloading {pkg_info.filename} ({pkg_info.size / 1024 / 1024:.1f} MB)[/dim]")

    try:
        req = Request(pkg_info.url, headers={"User-Agent": "repror/1.0"})
        with urlopen(req, timeout=300) as response:
            with open(dest_file, "wb") as f:
                f.write(response.read())

        # Verify hash if available
        if pkg_info.sha256:
            actual_hash = calculate_hash(dest_file)
            if actual_hash != pkg_info.sha256:
                print(f"[red]Hash mismatch for {pkg_info.filename}[/red]")
                return None

        return dest_file
    except Exception as e:
        logger.warning(f"Failed to download {pkg_info.url}: {e}")
        return None


def rebuild_package(package_file: Path, output_dir: Path) -> StreamingCmdOutput:
    """Rebuild a package using rattler-build rebuild."""
    rattler_bin = get_rattler_build()

    rebuild_command = [
        rattler_bin,
        "rebuild",
        "--package-file",
        str(package_file),
        "--output-dir",
        str(output_dir),
    ]

    return run_streaming_command(command=rebuild_command)


def sample_v1_packages(
    stats: FeedstockStats,
    sample_size: int,
    seed: Optional[int] = None,
) -> list[str]:
    """Randomly sample V1 packages."""
    if seed is not None:
        random.seed(seed)

    available = stats.v1_packages.copy()

    if sample_size >= len(available):
        print(
            f"[yellow]Requested sample size ({sample_size}) >= available packages ({len(available)}). Using all packages.[/yellow]"
        )
        return available

    sampled = random.sample(available, sample_size)
    print(f"[green]Sampled {len(sampled)} packages[/green]")
    return sampled


def _save_v1_result(v1_rebuild: V1Rebuild, patch: bool = False):
    """Save V1 rebuild result to database or patch file."""
    if patch:
        save_v1_patch(v1_rebuild)
    else:
        save(v1_rebuild)


def rebuild_v1_package(
    pkg_info: PackageInfo,
    work_dir: Path,
    build_tool_hash: str,
    platform: str,
    plat_version: str,
    actions_url: Optional[str] = None,
    patch: bool = False,
) -> V1RebuildResult:
    """Download and rebuild a single V1 package.

    Args:
        pkg_info: Package information from repodata
        work_dir: Working directory for downloads and rebuilds
        build_tool_hash: Hash of the build tool version
        platform: Platform name (linux, darwin, windows)
        plat_version: Platform version string
        actions_url: Optional GitHub Actions URL for tracking
        patch: If True, save to patch file instead of database (for CI)
    """
    print(f"[bold blue]Processing {pkg_info.name} {pkg_info.version}[/bold blue]")

    # Download the original package
    download_dir = work_dir / "downloads"
    download_dir.mkdir(exist_ok=True)

    original_file = download_package(pkg_info, download_dir)
    if original_file is None:
        # Save failed download
        v1_rebuild = V1Rebuild(
            package_name=pkg_info.name,
            version=pkg_info.version,
            original_url=pkg_info.url,
            original_hash=pkg_info.sha256,
            state=BuildState.FAIL,
            reason="Failed to download package",
            platform_name=platform,
            platform_version=plat_version,
            build_tool_hash=build_tool_hash,
            timestamp=datetime.now(),
            actions_url=actions_url,
        )
        _save_v1_result(v1_rebuild, patch)

        return V1RebuildResult(
            package_name=pkg_info.name,
            version=pkg_info.version,
            original_url=pkg_info.url,
            download_success=False,
            rebuild_success=False,
            reproducible=False,
            error_message="Failed to download package",
        )

    original_hash = calculate_hash(original_file)

    # Rebuild the package
    rebuild_dir = work_dir / "rebuild" / pkg_info.name
    rebuild_dir.mkdir(parents=True, exist_ok=True)

    output = rebuild_package(original_file, rebuild_dir)

    if output.return_code != 0:
        # Save failed rebuild
        v1_rebuild = V1Rebuild(
            package_name=pkg_info.name,
            version=pkg_info.version,
            original_url=pkg_info.url,
            original_hash=original_hash,
            state=BuildState.FAIL,
            reason=output.stderr[-1000:] if output.stderr else output.stdout[-1000:],
            platform_name=platform,
            platform_version=plat_version,
            build_tool_hash=build_tool_hash,
            timestamp=datetime.now(),
            actions_url=actions_url,
        )
        _save_v1_result(v1_rebuild, patch)

        return V1RebuildResult(
            package_name=pkg_info.name,
            version=pkg_info.version,
            original_url=pkg_info.url,
            download_success=True,
            rebuild_success=False,
            reproducible=False,
            original_hash=original_hash,
            error_message=f"Rebuild failed: {output.stderr[-200:] if output.stderr else output.stdout[-200:]}",
        )

    # Find the rebuilt package and calculate its hash
    try:
        rebuilt_file = find_conda_file(rebuild_dir)
        rebuild_hash = calculate_hash(rebuilt_file)
    except FileNotFoundError:
        v1_rebuild = V1Rebuild(
            package_name=pkg_info.name,
            version=pkg_info.version,
            original_url=pkg_info.url,
            original_hash=original_hash,
            state=BuildState.FAIL,
            reason="No output .conda file found after rebuild",
            platform_name=platform,
            platform_version=plat_version,
            build_tool_hash=build_tool_hash,
            timestamp=datetime.now(),
            actions_url=actions_url,
        )
        _save_v1_result(v1_rebuild, patch)

        return V1RebuildResult(
            package_name=pkg_info.name,
            version=pkg_info.version,
            original_url=pkg_info.url,
            download_success=True,
            rebuild_success=False,
            reproducible=False,
            original_hash=original_hash,
            error_message="No output .conda file found after rebuild",
        )

    is_reproducible = original_hash == rebuild_hash

    # Save successful rebuild
    v1_rebuild = V1Rebuild(
        package_name=pkg_info.name,
        version=pkg_info.version,
        original_url=pkg_info.url,
        original_hash=original_hash,
        rebuild_hash=rebuild_hash,
        state=BuildState.SUCCESS,
        platform_name=platform,
        platform_version=plat_version,
        build_tool_hash=build_tool_hash,
        timestamp=datetime.now(),
        actions_url=actions_url,
    )
    _save_v1_result(v1_rebuild, patch)

    return V1RebuildResult(
        package_name=pkg_info.name,
        version=pkg_info.version,
        original_url=pkg_info.url,
        download_success=True,
        rebuild_success=True,
        reproducible=is_reproducible,
        original_hash=original_hash,
        rebuild_hash=rebuild_hash,
    )


def run_v1_sample(
    sample_size: int = 10,
    seed: Optional[int] = None,
    actions_url: Optional[str] = None,
    specific_packages: Optional[list[str]] = None,
    subdir: Optional[str] = None,
    patch: bool = False,
) -> list[V1RebuildResult]:
    """
    Main function to sample and rebuild V1 packages from conda-forge.

    Args:
        sample_size: Number of packages to sample (ignored if specific_packages provided)
        seed: Random seed for reproducible sampling
        actions_url: Optional GitHub Actions URL for tracking
        specific_packages: Optional list of specific package names to process
        subdir: Optional conda subdir (e.g., 'linux-64', 'osx-arm64')
        patch: If True, save to patch files instead of database (for CI)

    Returns:
        List of V1RebuildResult objects
    """
    # Determine subdir
    if subdir is None:
        subdir = get_subdir()
    print(f"[dim]Using subdir: {subdir}[/dim]")

    # Fetch stats
    stats = fetch_feedstock_stats()
    print(f"[dim]Stats last updated: {stats.last_updated}[/dim]")
    print(
        f"[dim]Total feedstocks: {stats.total_feedstocks}, V1: {stats.recipe_v1_count}, meta.yaml: {stats.meta_yaml_count}[/dim]"
    )

    # Fetch repodata
    print("[dim]Fetching conda-forge repodata (this may take a moment)...[/dim]")
    repodata = fetch_repodata(subdir)
    print(f"[dim]Repodata contains {len(repodata.get('packages.conda', {}))} .conda packages[/dim]")

    # Determine packages to process
    if specific_packages:
        # Filter to only include packages that are actually V1
        packages_to_process = [
            p for p in specific_packages if p in stats.v1_packages
        ]
        if len(packages_to_process) != len(specific_packages):
            not_v1 = set(specific_packages) - set(packages_to_process)
            print(
                f"[yellow]Warning: These packages are not V1 recipes: {not_v1}[/yellow]"
            )
    else:
        packages_to_process = sample_v1_packages(stats, sample_size, seed)

    if not packages_to_process:
        print("[red]No packages to process[/red]")
        return []

    # Find packages in repodata
    packages_found: list[PackageInfo] = []
    packages_not_found: list[str] = []

    for pkg_name in packages_to_process:
        pkg_info = find_package_in_repodata(pkg_name, repodata, subdir)
        if pkg_info:
            packages_found.append(pkg_info)
        else:
            packages_not_found.append(pkg_name)

    if packages_not_found:
        print(f"[yellow]Warning: {len(packages_not_found)} packages not found in repodata for {subdir}:[/yellow]")
        for pkg in packages_not_found[:10]:
            print(f"  - {pkg}")
        if len(packages_not_found) > 10:
            print(f"  ... and {len(packages_not_found) - 10} more")

    print(f"[green]Found {len(packages_found)} packages in conda-forge {subdir}[/green]")

    if not packages_found:
        print("[red]No packages found in repodata[/red]")
        return []

    # Setup build info
    build_tool = rattler_build_hash()
    platform = platform_name()
    plat_version = platform_version()

    results: list[V1RebuildResult] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        work_dir = Path(tmp_dir)

        for i, pkg_info in enumerate(packages_found, 1):
            print(f"\n[bold]({i}/{len(packages_found)}) {pkg_info.name} {pkg_info.version}[/bold]")
            result = rebuild_v1_package(
                pkg_info, work_dir, build_tool, platform, plat_version, actions_url, patch
            )
            results.append(result)

            # Print result summary
            if result.rebuild_success:
                if result.reproducible:
                    print(f"[green]✓ {result.package_name}: Reproducible![/green]")
                else:
                    print(f"[yellow]✗ {result.package_name}: Not reproducible[/yellow]")
                    print(f"  Original hash: {result.original_hash}")
                    print(f"  Rebuild hash:  {result.rebuild_hash}")
            elif result.download_success:
                print(f"[red]✗ {result.package_name}: Rebuild failed[/red]")
            else:
                print(f"[red]✗ {result.package_name}: Download failed[/red]")

    return results


def print_summary(results: list[V1RebuildResult]) -> None:
    """Print a summary of the rebuild results."""
    total = len(results)
    if total == 0:
        print("[yellow]No results to summarize[/yellow]")
        return

    download_success = sum(1 for r in results if r.download_success)
    rebuild_success = sum(1 for r in results if r.rebuild_success)
    reproducible = sum(1 for r in results if r.reproducible)

    print("\n" + "=" * 50)
    print("[bold]V1 Recipe Rebuild Summary[/bold]")
    print("=" * 50)
    print(f"Total packages processed:  {total}")
    print(f"Successful downloads:      {download_success}/{total} ({100*download_success/total:.1f}%)")
    print(f"Successful rebuilds:       {rebuild_success}/{total} ({100*rebuild_success/total:.1f}%)")
    print(f"Reproducible:              {reproducible}/{total} ({100*reproducible/total:.1f}%)")

    if rebuild_success > 0:
        repro_rate = 100 * reproducible / rebuild_success
        print(f"Reproducibility rate:      {reproducible}/{rebuild_success} ({repro_rate:.1f}% of successful rebuilds)")

    if rebuild_success > 0 and reproducible < rebuild_success:
        print("\n[yellow]Non-reproducible packages:[/yellow]")
        for r in results:
            if r.rebuild_success and not r.reproducible:
                print(f"  - {r.package_name} {r.version}")

    failed_downloads = [r for r in results if not r.download_success]
    if failed_downloads:
        print("\n[red]Failed to download:[/red]")
        for r in failed_downloads:
            print(f"  - {r.package_name}: {r.error_message}")

    failed_rebuilds = [r for r in results if r.download_success and not r.rebuild_success]
    if failed_rebuilds:
        print("\n[red]Failed to rebuild:[/red]")
        for r in failed_rebuilds[:10]:
            print(f"  - {r.package_name} {r.version}")
        if len(failed_rebuilds) > 10:
            print(f"  ... and {len(failed_rebuilds) - 10} more")


# Typer app for CLI
app = typer.Typer()


@app.command()
def sample(
    sample_size: Annotated[
        int, typer.Option("--size", "-n", help="Number of packages to sample")
    ] = 10,
    seed: Annotated[
        Optional[int], typer.Option("--seed", "-s", help="Random seed for reproducible sampling")
    ] = None,
    packages: Annotated[
        Optional[list[str]], typer.Option("--package", "-p", help="Specific packages to process (can be repeated)")
    ] = None,
    subdir: Annotated[
        Optional[str], typer.Option("--subdir", help="Conda subdir (e.g., linux-64, osx-arm64)")
    ] = None,
    actions_url: Annotated[
        Optional[str], typer.Option(help="GitHub Actions URL for tracking")
    ] = None,
    patch: Annotated[
        bool, typer.Option(help="Save to patch files instead of database (for CI)")
    ] = False,
):
    """
    Sample and rebuild V1 recipe packages from conda-forge.

    Downloads existing .conda packages from conda-forge and attempts to
    rebuild them using rattler-build rebuild to check reproducibility.
    """
    results = run_v1_sample(
        sample_size=sample_size,
        seed=seed,
        actions_url=actions_url,
        specific_packages=packages,
        subdir=subdir,
        patch=patch,
    )
    print_summary(results)


@app.command()
def list_v1(
    limit: Annotated[
        int, typer.Option("--limit", "-l", help="Maximum number of packages to list")
    ] = 50,
    subdir: Annotated[
        Optional[str], typer.Option("--subdir", help="Filter by packages available in this subdir")
    ] = None,
):
    """
    List available V1 recipe packages.
    """
    stats = fetch_feedstock_stats()
    packages = sorted(stats.v1_packages)

    if subdir:
        print(f"[dim]Checking availability in {subdir}...[/dim]")
        repodata = fetch_repodata(subdir)
        available_names = {
            info.get("name")
            for info in repodata.get("packages.conda", {}).values()
        }
        packages = [p for p in packages if p in available_names]
        print(f"[dim]{len(packages)} V1 packages available in {subdir}[/dim]")

    display_packages = packages[:limit]

    print(f"\n[bold]V1 Recipe Packages ({len(packages)} total, showing {len(display_packages)}):[/bold]")
    for pkg in display_packages:
        print(f"  - {pkg}")

    if len(packages) > limit:
        print(f"\n[dim]... and {len(packages) - limit} more[/dim]")


@app.command()
def stats():
    """
    Show statistics about V1 recipe adoption.
    """
    feedstock_stats = fetch_feedstock_stats()

    total = feedstock_stats.total_feedstocks
    v1_pct = 100 * feedstock_stats.recipe_v1_count / total if total > 0 else 0
    meta_pct = 100 * feedstock_stats.meta_yaml_count / total if total > 0 else 0

    print("\n[bold]Are We Recipe V1 Yet? Statistics[/bold]")
    print("=" * 45)
    print(f"Last updated:     {feedstock_stats.last_updated}")
    print(f"Total feedstocks: {total:,}")
    print(f"V1 recipes:       {feedstock_stats.recipe_v1_count:,} ({v1_pct:.1f}%)")
    print(f"meta.yaml:        {feedstock_stats.meta_yaml_count:,} ({meta_pct:.1f}%)")
    print(f"Unknown:          {feedstock_stats.unknown_count:,}")


@app.command()
def check(
    packages: Annotated[
        list[str], typer.Argument(help="Package names to check")
    ],
    subdir: Annotated[
        Optional[str], typer.Option("--subdir", help="Conda subdir to check")
    ] = None,
):
    """
    Check if specific packages have V1 recipes and are available on conda-forge.
    """
    stats = fetch_feedstock_stats()

    if subdir is None:
        subdir = get_subdir()

    repodata = fetch_repodata(subdir)

    print(f"\n[bold]Package Status ({subdir}):[/bold]")
    for pkg_name in packages:
        is_v1 = pkg_name in stats.v1_packages
        pkg_info = find_package_in_repodata(pkg_name, repodata, subdir)

        status_parts = []
        if is_v1:
            status_parts.append("[green]V1[/green]")
        else:
            status_parts.append("[yellow]meta.yaml[/yellow]")

        if pkg_info:
            status_parts.append(f"[green]available[/green] ({pkg_info.version})")
        else:
            status_parts.append("[red]not in repodata[/red]")

        print(f"  {pkg_name}: {' | '.join(status_parts)}")
