import asyncio
import functools
import time
from logging import Logger
from typing import Any, Callable, TypeVar, cast


T = TypeVar("T", bound=Callable[..., Any])

class TimeExecutioner:

    _logger = Logger(__name__)

    @property
    def logger(self) -> Logger:
        return self._logger


    def set_logger(self, logger) -> None:
        self._logger = logger


    @staticmethod
    def log(f_py:Any=None, log_level:str="info") -> None:
        assert callable(f_py) or f_py is None

        """
        the outer decorator function for time executioner logging. Because of how decorators
        work, in python, we need to nest the outer decorator inside that takes arguments around
        the core inner decorator. (See: https://stackoverflow.com/a/60832711)
        
        Parameters:
            f_py (Callable): function to be decorated, or None.
                  When calling @TimeExecutioner.log with no arguments, f_py is the function. 
                  When calling @TimeExecutioner.log(log_level="debug"), f_py is None.
                  
            log_level (str): log level to use for logging. Defaults to "info".):
        
        Returns: None
        """

        def _run(func: T) -> T:
            """
            The base decorator that measures and logs the execution time of both sync and async methods.

            Args:
                func: The function to be timed (can be either sync or async)

            Returns:
                Wrapped function that logs its execution time
            """

            def _log_execution(
                start_time: float, func_name: str, class_name: str, error: Exception | None = None
            ) -> None:
                """
                Helper function to handle logging logic
                """
                execution_time = time.time() - start_time
                executioner = TimeExecutioner()

                if error is None:
                    executioner.logger.log(
                        log_level,
                        f"{class_name}.{func_name}() executed in {execution_time:.3f} seconds",
                        extra={
                            "function_name": func_name,
                            "class_name": class_name,
                            "execution_time": execution_time,
                            "is_async": asyncio.iscoroutinefunction(func),
                        },
                    )
                else:
                    executioner.logger.error(
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