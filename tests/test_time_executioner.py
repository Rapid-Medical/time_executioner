import asyncio
import logging
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from time_executioner import TimeExecutioner


# Test classes and functions
class TestClass:
    @TimeExecutioner.log
    def sync_method(self, x: int) -> int:
        time.sleep(0.1)
        return x * 2

    @TimeExecutioner.log
    async def async_method(self, x: int) -> int:
        await asyncio.sleep(0.1)
        return x * 2

    @TimeExecutioner.log(log_level="debug")
    def sync_method_log_level(self, x: int) -> int:
        time.sleep(0.1)
        return x * 3

    @TimeExecutioner.log()
    def sync_method_log_level_no_args(self, x: int) -> int:
        time.sleep(0.1)
        return x * 4

    @TimeExecutioner.log
    def error_method(self) -> None:
        raise ValueError("Test error")

    @TimeExecutioner.log
    async def async_error_method(self) -> None:
        await asyncio.sleep(0.1)
        raise ValueError("Test async error")


@TimeExecutioner.log
def standalone_sync_function(x: int) -> int:
    time.sleep(0.1)
    return x * 2


@TimeExecutioner.log
async def standalone_async_function(x: int) -> int:
    await asyncio.sleep(0.1)
    return x * 2


@TimeExecutioner.log(log_level="warning")
def standalone_sync_function_with_log_level(x: int) -> int:
    time.sleep(0.1)
    return x * 2


@pytest.fixture(autouse=True)
def restore_global_logger():
    """set_logger mutates process-wide state; never let it leak between tests."""
    original = TimeExecutioner._logger
    yield
    TimeExecutioner._logger = original


@pytest.fixture
def mock_logger():
    logger = Mock()
    with patch.object(TimeExecutioner, "_logger", logger):
        yield logger


class CustomLogger(logging.Logger):
    log_was_called = False

    def log(self, level, msg, *args, **kwargs) -> None:
        self.log_was_called = True


class TestTimeExecutionDecorator:
    def test_sync_method(self, mock_logger: MagicMock) -> None:
        test_instance = TestClass()
        result = test_instance.sync_method(5)

        assert result == 10
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.INFO
        assert "TestClass.sync_method(): executed in" in call_args[0][1]
        assert call_args[1]["extra"]["function_name"] == "sync_method()"
        assert call_args[1]["extra"]["class_name"] == "TestClass"
        assert not call_args[1]["extra"]["is_async"]
        assert isinstance(call_args[1]["extra"]["execution_time"], float)

    @pytest.mark.asyncio
    async def test_async_method(self, mock_logger: MagicMock) -> None:
        test_instance = TestClass()
        result = await test_instance.async_method(5)

        assert result == 10
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert "TestClass.async_method(): executed in" in call_args[0][1]
        assert call_args[1]["extra"]["function_name"] == "async_method()"
        assert call_args[1]["extra"]["class_name"] == "TestClass"
        assert call_args[1]["extra"]["is_async"]
        assert isinstance(call_args[1]["extra"]["execution_time"], float)

    def test_log_level_specified(self, mock_logger: MagicMock) -> None:
        test_instance = TestClass()
        result = test_instance.sync_method_log_level(5)

        assert result == 15
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.DEBUG
        assert "TestClass.sync_method_log_level(): executed in" in call_args[0][1]

    def test_log_level_specified_no_args(self, mock_logger: MagicMock) -> None:
        test_instance = TestClass()
        result = test_instance.sync_method_log_level_no_args(5)

        assert result == 20
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.INFO

    def test_standalone_sync_function(self, mock_logger: MagicMock) -> None:
        result = standalone_sync_function(5)

        assert result == 10
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert ".standalone_sync_function(): executed in" in call_args[0][1]
        assert call_args[1]["extra"]["function_name"] == "standalone_sync_function()"
        assert call_args[1]["extra"]["class_name"] == "int"
        assert not call_args[1]["extra"]["is_async"]

    @pytest.mark.asyncio
    async def test_standalone_async_function(self, mock_logger: MagicMock) -> None:
        result = await standalone_async_function(5)

        assert result == 10
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert ".standalone_async_function(): executed in" in call_args[0][1]
        assert call_args[1]["extra"]["function_name"] == "standalone_async_function()"
        assert call_args[1]["extra"]["class_name"] == "int"
        assert call_args[1]["extra"]["is_async"]

    def test_log_level_specified_standalone(self, mock_logger: MagicMock) -> None:
        result = standalone_sync_function_with_log_level(5)
        assert result == 10
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.WARNING

    def test_sync_error_handling(self, mock_logger: MagicMock) -> None:
        test_instance = TestClass()

        with pytest.raises(ValueError, match="Test error"):
            test_instance.error_method()

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Error in TestClass.error_method" in call_args[0][0]
        assert call_args[1]["extra"]["error"] == "Test error"
        assert not call_args[1]["extra"]["is_async"]

    @pytest.mark.asyncio
    async def test_async_error_handling(self, mock_logger: MagicMock) -> None:
        test_instance = TestClass()

        with pytest.raises(ValueError, match="Test async error"):
            await test_instance.async_error_method()

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Error in TestClass.async_error_method" in call_args[0][0]
        assert call_args[1]["extra"]["error"] == "Test async error"
        assert call_args[1]["extra"]["is_async"]

    def test_execution_time_measurement(self, mock_logger: MagicMock) -> None:
        test_instance = TestClass()
        start = time.time()
        test_instance.sync_method(5)
        end = time.time()

        call_args = mock_logger.log.call_args
        measured_time = call_args[1]["extra"]["execution_time"]
        assert measured_time <= (end - start)
        assert measured_time >= 0.1  # Since we sleep for 0.1 seconds

    def test_with_real_logger(self) -> None:
        test_instance = TestClass()
        result = test_instance.sync_method(5)

        assert result == 10

    def test_with_custom_logger(self) -> None:
        custom_logger = CustomLogger("test_logger")
        TimeExecutioner.set_logger(custom_logger)
        test_instance = TestClass()
        _ = test_instance.sync_method(5)
        assert custom_logger.log_was_called is True


class TestTimeExecuteContextManager:
    def test_time_execute_context_manager(self, mock_logger: MagicMock) -> None:
        with TimeExecutioner.time("test_label"):
            time.sleep(0.1)

        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.INFO
        assert "time_execute.test_label: executed in" in call_args[0][1]
        assert call_args[1]["extra"]["function_name"] == "test_label"
        assert call_args[1]["extra"]["class_name"] == "time_execute"
        assert not call_args[1]["extra"]["is_async"]
        assert isinstance(call_args[1]["extra"]["execution_time"], float)

    def test_time_execute_context_manager_with_log_level(self, mock_logger: MagicMock) -> None:
        with TimeExecutioner.time("test_label", log_level="warning"):
            time.sleep(0.1)

        assert mock_logger.log.call_args[0][0] == logging.WARNING

    def test_including_extra_data(self, mock_logger: MagicMock) -> None:
        with TimeExecutioner.time("test_label", extra={"extra_key": "extra_value"}):
            time.sleep(0.1)

        assert mock_logger.log.call_args[1]["extra"]["extra_key"] == "extra_value"


class TestLoggerConfiguration:
    """The default logger is process-wide state, so a per-use override has to
    exist for two consumers in one process not to clobber each other."""

    def test_per_call_logger_on_decorator(self) -> None:
        mine = Mock()

        @TimeExecutioner.log(logger=mine)
        def work(x: int) -> int:
            return x * 2

        assert work(5) == 10
        mine.log.assert_called_once()

    def test_per_call_logger_leaves_global_untouched(self) -> None:
        before = TimeExecutioner._logger
        mine = Mock()

        @TimeExecutioner.log(logger=mine)
        def work() -> None:
            pass

        work()
        assert TimeExecutioner._logger is before

    def test_per_call_logger_wins_over_global(self) -> None:
        theirs, mine = Mock(), Mock()
        TimeExecutioner.set_logger(theirs)

        @TimeExecutioner.log(logger=mine)
        def work() -> None:
            pass

        work()
        mine.log.assert_called_once()
        theirs.log.assert_not_called()

    @pytest.mark.asyncio
    async def test_per_call_logger_on_async_decorator(self) -> None:
        mine = Mock()

        @TimeExecutioner.log(logger=mine)
        async def work(x: int) -> int:
            return x * 2

        assert await work(5) == 10
        mine.log.assert_called_once()

    def test_per_call_logger_on_context_manager(self) -> None:
        theirs, mine = Mock(), Mock()
        TimeExecutioner.set_logger(theirs)

        with TimeExecutioner.time("block", logger=mine):
            pass

        mine.log.assert_called_once()
        theirs.log.assert_not_called()

    def test_per_call_logger_receives_errors(self) -> None:
        mine = Mock()

        @TimeExecutioner.log(logger=mine)
        def boom() -> None:
            raise ValueError("nope")

        with pytest.raises(ValueError, match="nope"):
            boom()

        mine.error.assert_called_once()

    def test_reset_logger_restores_the_default(self) -> None:
        TimeExecutioner.set_logger(Mock())
        TimeExecutioner.reset_logger()

        assert isinstance(TimeExecutioner._logger, logging.Logger)
        assert TimeExecutioner._logger.name == "time_executioner._core"
