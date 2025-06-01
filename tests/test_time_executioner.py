import asyncio
import time
from unittest.mock import patch, Mock

import pytest

from time_executioner import time_executioner
from time_executioner.time_executioner import TimeExecutioner


# Test classes and functions
class TestClass:
    @TimeExecutioner.run
    def sync_method(self, x: int) -> int:
        time.sleep(0.1)
        return x * 2

    @TimeExecutioner.run
    async def async_method(self, x: int) -> int:
        await asyncio.sleep(0.1)
        return x * 2

    @TimeExecutioner.run
    def error_method(self) -> None:
        raise ValueError("Test error")

    @TimeExecutioner.run
    async def async_error_method(self) -> None:
        await asyncio.sleep(0.1)
        raise ValueError("Test async error")


@TimeExecutioner.run
def standalone_sync_function(x: int) -> int:
    time.sleep(0.1)
    return x * 2


@TimeExecutioner.run
async def standalone_async_function(x: int) -> int:
    await asyncio.sleep(0.1)
    return x * 2


@pytest.fixture
def mock_logger():
    logger = Mock()
    with patch.object(TimeExecutioner, '_logger', logger):
        yield logger


@pytest.mark.asyncio
class TestTimeExecution:
    async def test_sync_method(self, mock_logger) -> None:
        test_instance = TestClass()
        result = test_instance.sync_method(5)

        assert result == 10
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "TestClass.sync_method() executed in" in call_args[0][0]
        assert call_args[1]["extra"]["function_name"] == "sync_method"
        assert call_args[1]["extra"]["class_name"] == "TestClass"
        assert not call_args[1]["extra"]["is_async"]
        assert isinstance(call_args[1]["extra"]["execution_time"], float)

    async def test_async_method(self, mock_logger):
        test_instance = TestClass()
        result = await test_instance.async_method(5)

        assert result == 10
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "TestClass.async_method() executed in" in call_args[0][0]
        assert call_args[1]["extra"]["function_name"] == "async_method"
        assert call_args[1]["extra"]["class_name"] == "TestClass"
        assert call_args[1]["extra"]["is_async"]
        assert isinstance(call_args[1]["extra"]["execution_time"], float)

    def test_standalone_sync_function(self, mock_logger):
        result = standalone_sync_function(5)

        assert result == 10
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert ".standalone_sync_function() executed in" in call_args[0][0]
        assert call_args[1]["extra"]["function_name"] == "standalone_sync_function"
        assert call_args[1]["extra"]["class_name"] == "int"
        assert not call_args[1]["extra"]["is_async"]

    async def test_standalone_async_function(self, mock_logger):
        """Test standalone asynchronous function execution and logging"""
        result = await standalone_async_function(5)

        assert result == 10
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert ".standalone_async_function() executed in" in call_args[0][0]
        assert call_args[1]["extra"]["function_name"] == "standalone_async_function"
        assert call_args[1]["extra"]["class_name"] == "int"
        assert call_args[1]["extra"]["is_async"]

    def test_sync_error_handling(self, mock_logger):
        test_instance = TestClass()

        with pytest.raises(ValueError, match="Test error"):
            test_instance.error_method()

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Error in TestClass.error_method" in call_args[0][0]
        assert call_args[1]["extra"]["error"] == "Test error"
        assert not call_args[1]["extra"]["is_async"]

    async def test_async_error_handling(self, mock_logger):
        test_instance = TestClass()

        with pytest.raises(ValueError, match="Test async error"):
            await test_instance.async_error_method()

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Error in TestClass.async_error_method" in call_args[0][0]
        assert call_args[1]["extra"]["error"] == "Test async error"
        assert call_args[1]["extra"]["is_async"]

    def test_execution_time_measurement(self, mock_logger):
        test_instance = TestClass()
        start = time.time()
        test_instance.sync_method(5)
        end = time.time()

        call_args = mock_logger.info.call_args
        measured_time = call_args[1]["extra"]["execution_time"]
        assert measured_time <= (end - start)
        assert measured_time >= 0.1  # Since we sleep for 0.1 seconds
