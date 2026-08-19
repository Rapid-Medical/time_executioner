import functools
import inspect
import logging
import time
from contextlib import contextmanager
from logging import Logger
from typing import Any, Callable, Generator, Optional, TypeVar, cast

from ._accumulator import PhaseAccumulator

T = TypeVar("T", bound=Callable[..., Any])

_DEFAULT_LOGGER: Logger = logging.getLogger(__name__)


class TimeExecutioner:
    """
    A class for logging execution times of synchronous and asynchronous functions.

    This class provides functionality to log execution time for methods using a decorator.
    It supports different log levels and allows customization of the logger instance.
    Additionally, it handles exceptions during execution and logs the error details. The
    class aims to provide a systematic and reusable approach to monitoring performance
    metrics and debugging function executions.

    Defaults to using the built-in logging module, however, it can be customized to use
    anything that implements the logging.Logger interface.
    """

    _logger: Logger = _DEFAULT_LOGGER  # Class-level logger

    @classmethod
    def set_logger(cls, logger: Logger) -> None:
        """
        Set the default logger for every TimeExecutioner use in this process.

        This is process-wide state: the last caller wins. If you are a library,
        or otherwise share a process with code you do not control, prefer the
        per-use `logger=` argument on `log()` and `time()`, which overrides this
        default without mutating it.
        """
        cls._logger = logger

    @classmethod
    def reset_logger(cls) -> None:
        """Restore the built-in default logger, discarding any set_logger() call."""
        cls._logger = _DEFAULT_LOGGER

    @property
    def logger(self) -> Logger:
        """Get the current logger instance."""
        return self._logger

    @staticmethod
    def _log_execution(
        log_level: str,
        start_time: float,
        func_name: str,
        class_name: str,
        is_async: Optional[bool] = False,
        extra: Optional[dict[str, Any]] = None,
        error: Optional[Exception | None] = None,
        logger: Optional[Logger] = None,
        summary: Optional[str] = None,
    ) -> None:
        """
        Helper function to handle logging logic.

        When `summary` is given it replaces the generated message on both the
        success and error branches. Callers that pass it own the whole line,
        including any error text; this keeps phase formatting out of here.
        """

        execution_time = time.perf_counter() - start_time
        active_logger = logger if logger is not None else TimeExecutioner._logger

        # when calling logger.log, you're expected to pass in an int level.
        # however, the inbuilt logging.getLevelName() is a mess. this
        # names mapping method is only available in newer versions of python.
        int_level = logging.getLevelNamesMapping()[log_level.upper()]

        payload = {
            "function_name": func_name,
            "class_name": class_name,
            "execution_time": execution_time,
            **({"is_async": is_async} if is_async is not None else {}),
            **({"error": str(error)} if error is not None else {}),
        }

        if extra is not None:
            payload = payload | extra

        if error is None:
            active_logger.log(
                int_level,
                (
                    summary
                    if summary is not None
                    else f"{class_name}.{func_name}: executed in {execution_time:.3f} seconds"
                ),
                extra=payload,
            )
        else:
            active_logger.error(
                (
                    summary
                    if summary is not None
                    else f"Error in {class_name}.{func_name}: {str(error)}"
                ),
                extra=payload,
            )

    @staticmethod
    def log(f_py: Any = None, log_level: str = "info", logger: Optional[Logger] = None):
        """
        the outer decorator function for time executioner logging. Because of how decorators
        work, in python, we need to nest the core decorator function inside another decorator
        that takes arguments. (See: https://stackoverflow.com/a/60832711)

        Parameters:
            f_py (Callable): function to be decorated, or None.
                  When calling @TimeExecutioner.log with no arguments, f_py is the function.
                  When calling @TimeExecutioner.log(log_level="debug"), f_py is None,
                  but calls _run with the function context.

            log_level (str): log level to use for logging. Defaults to "info".

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

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.perf_counter()
                func_name = f"{func.__name__}()"
                class_name = args[0].__class__.__name__ if args else ""
                is_async = inspect.iscoroutinefunction(func)
                try:
                    result = await func(*args, **kwargs)
                    TimeExecutioner._log_execution(
                        log_level, start_time, func_name, class_name, is_async, logger=logger
                    )

                    return result
                except Exception as e:
                    TimeExecutioner._log_execution(
                        log_level,
                        start_time,
                        func_name,
                        class_name,
                        is_async,
                        error=e,
                        logger=logger,
                    )
                    raise

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.perf_counter()
                func_name = f"{func.__name__}()"
                class_name = args[0].__class__.__name__ if args else ""
                is_async = inspect.iscoroutinefunction(func)

                try:
                    result = func(*args, **kwargs)
                    TimeExecutioner._log_execution(
                        log_level, start_time, func_name, class_name, is_async, logger=logger
                    )
                    return result
                except Exception as e:
                    TimeExecutioner._log_execution(
                        log_level,
                        start_time,
                        func_name,
                        class_name,
                        is_async,
                        error=e,
                        logger=logger,
                    )
                    raise

            return cast(T, async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper)

        return _run(f_py) if callable(f_py) else _run

    @staticmethod
    @contextmanager
    def time(
        label: str,
        log_level: str = "info",
        extra: dict[str, Any] | None = None,
        logger: Logger | None = None,
    ) -> Generator[Any, None, None]:
        """
        a context manager for time executioner logging. Allows you to time and log a block of code.

        Args:
            label (str): a label to identify the block of code
            log_level (str): an optional log level to use for logging. Defaults to "info".
            extra (dict): an optional dictionary of extra data to include in the log message
        """

        start_time = time.perf_counter()
        try:
            yield
        finally:
            msg = f"{label}"
            TimeExecutioner._log_execution(
                log_level, start_time, msg, "time_execute", extra=extra, logger=logger
            )

    @staticmethod
    @contextmanager
    def accumulate(
        label: str,
        log_level: str = "info",
        extra: dict[str, Any] | None = None,
        logger: Logger | None = None,
    ) -> Generator[PhaseAccumulator, None, None]:
        """
        Accumulate many timed blocks and log one summary line on exit.

        Where `time()` logs on every context exit, this logs once, so timing a
        phase inside a ten-thousand-iteration loop costs one line instead of ten
        thousand. The yielded accumulator offers `time(label)` for phases and
        `count(name, n=1)` for tallies.

        The reported `unaccounted` figure is wall clock minus the sum of the
        phases: the time that went somewhere nobody thought to measure.

        On an exception the summary is logged at error level with the breakdown
        intact and the exception propagates, so a run that dies still reports
        where its time went.

        Args:
            label (str): a label identifying the run
            log_level (str): log level for the summary. Defaults to "info".
            extra (dict): extra data for the log record; wins over the keys this
                adds ("phases", "counts", "unaccounted")
            logger (Logger): a logger for this use only, overriding the default.
                Resolved once on entry, and used for the summary and for any
                overlap warning.
        """
        active_logger = logger if logger is not None else TimeExecutioner._logger
        accumulator = PhaseAccumulator(label, active_logger)

        start_time = time.perf_counter()
        error: Exception | None = None
        try:
            yield accumulator
        except Exception as e:
            error = e
            raise
        finally:
            wall = time.perf_counter() - start_time
            payload = accumulator.payload(wall)
            # _log_execution derives execution_time from start_time a few
            # microseconds after `wall` is taken. Override it so the record
            # closes on itself: execution_time - sum(phases) == unaccounted,
            # and the payload agrees with the `total=` in the message.
            payload["execution_time"] = wall
            if extra is not None:
                payload = payload | extra

            TimeExecutioner._log_execution(
                log_level,
                start_time,
                label,
                "time_accumulate",
                extra=payload,
                error=error,
                summary=accumulator.summary(wall, error),
                logger=active_logger,
            )
