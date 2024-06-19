class GlobalOptions:
    """Global options for the CLI."""

    skip_setup_rattler_build: bool = False
    in_memory_sql: bool = False


global_options = GlobalOptions()
