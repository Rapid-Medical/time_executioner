"""
Time Executioner - A decorator and context manager for measuring execution time of functions
"""

from ._accumulator import PhaseAccumulator
from ._core import TimeExecutioner

__version__ = "0.1.0"

__all__ = ["PhaseAccumulator", "TimeExecutioner", "__version__", "describe"]


def describe() -> None:
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
        "        ...\n\n"
        "  Or accumulate many phases into one summary line:\n"
        "    with TimeExecutioner.accumulate('batch') as phases:\n"
        "        for item in items:\n"
        "            with phases.time('fetch'):\n"
        "                ...\n"
    ).format(__version__)
    print(description)
