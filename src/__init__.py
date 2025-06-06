"""
Time Executioner - A decorator for measuring execution time of functions
"""


def __version__():
    """Return the version of the simple_stats package."""
    return "0.0.2"


def describe():
    """Print a description of the package and its features."""
    description = (
        "Time Executioner\n"
        "Version: {}\n"
        "Provides a simple decorator for wrapping and logging execution time. \n"
        "  Example:\n"
        "    @TimeExecutioner.log\n"
        "    def my_method_to_time(): \n"
        "        ...\n\n"
        "  Or with a log level as an argument:\n"
        "    @TimeExecutioner.log(log_level='debug')\n"
        "    def my_method_to_time(): \n"
        "        ...\n"
    ).format(__version__())
    print(description)
