import asyncio
import functools
import logging
import time
from logging import Logger
from typing import Any, Callable, TypeVar, cast

T = TypeVar("T", bound=Callable[..., Any])


class TimeExecutioner:
    """
    A class for logging execution times of synchronous and asynchronous functions.

    This class provides functionality to log execution time for methods using a decorator.
    It supports different log levels and allows customization of the logger instance.
    Additionally, it handles exceptions during execution and logs the error details. The
    class aims to provide a systematic and reusable approach to monitoring performance
    metrics and debugging function executions.

    Defaults to using the built-in logging module, however it can be customized to use
    anything that implements the logging.Logger interface.
    """

    _logger: Logger = logging.getLogger(__name__)  # Class-level logger

    @classmethod
    def set_logger(cls, logger: Logger) -> None:
        """Set a custom logger for the TimeExecutioner class."""
        cls._logger = logger

    @property
    def logger(self) -> Logger:
        """Get the current logger instance."""
        return self._logger

    @staticmethod
    def log(f_py: Any = None, log_level: str = "info"):
        """
        the outer decorator function for time executioner logging. Because of how decorators
        work, in python, we need to nest the core decorator function inside another decorator
        that takes arguments. (See: https://stackoverflow.com/a/60832711)

        Parameters:
            f_py (Callable): function to be decorated, or None.
                  When calling @TimeExecutioner.log with no arguments, f_py is the function.
                  When calling @TimeExecutioner.log(log_level="debug"), f_py is None,
                  but calls _run with the function context.

            log_level (str): log level to use for logging. Defaults to "info".):

        Returns: None
        """

        def _run(func: T) -> T:
            """
            The base decorator that measures and logs the execution time of both sync
            and async methods.

            Args:
                func: The function to be timed (can be either sync or async)

            Returns:
                Wrapped function that logs its execution time
            """

            def _log_execution(
                start_time: float,
                func_name: str,
                class_name: str,
                error: Exception | None = None,
            ) -> None:
                """
                Helper function to handle logging logic
                """
                execution_time = time.time() - start_time
                te = TimeExecutioner()

                # when calling logger.log, you're expected to pass in an int level.
                # however the inbuilt logging.getLevelName() is a mess. this
                # names mapping method is only available in newer versions of python.
                int_level = logging.getLevelNamesMapping()[log_level.upper()]

                if error is None:
                    te.logger.log(
                        int_level,
                        f"{class_name}.{func_name}() executed in {execution_time:.3f} seconds",
                        extra={
                            "function_name": func_name,
                            "class_name": class_name,
                            "execution_time": execution_time,
                            "is_async": asyncio.iscoroutinefunction(func),
                        },
                    )
                else:
                    te.logger.error(
                        f"Error in {class_name}.{func_name}: {str(error)}",
                        extra={
                            "function_name": func_name,
                            "class_name": class_name,
                            "execution_time": execution_time,
                            "is_async": asyncio.iscoroutinefunction(func),
                            "error": str(error),
                        },
                    )

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                class_name = args[0].__class__.__name__ if args else ""

                try:
                    result = await func(*args, **kwargs)
                    _log_execution(start_time, func.__name__, class_name)
                    return result
                except Exception as e:
                    _log_execution(start_time, func.__name__, class_name, error=e)
                    raise

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                class_name = args[0].__class__.__name__ if args else ""

                try:
                    result = func(*args, **kwargs)
                    _log_execution(start_time, func.__name__, class_name)
                    return result
                except Exception as e:
                    _log_execution(start_time, func.__name__, class_name, error=e)
                    raise

            return cast(T, async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper)

        return _run(f_py) if callable(f_py) else _run
