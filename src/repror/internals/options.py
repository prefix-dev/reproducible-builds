class GlobalOptions:
    """Global options for the CLI."""

    skip_setup_rattler_build: bool = False
    in_memory_sql: bool = False
    # This is a global option to skip the output of the command
    # This is useful when we want to run a command and not show the output
    # when generating recipe names that are used to start dynamic jobs
    no_output: bool = False


global_options = GlobalOptions()
