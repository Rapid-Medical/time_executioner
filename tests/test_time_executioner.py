import asyncio
import logging
import threading
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from time_executioner import PhaseAccumulator, TimeExecutioner


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


class TestLogExecutionSummaryOverride:
    def test_summary_replaces_the_success_message(self) -> None:
        logger = Mock()

        TimeExecutioner._log_execution(
            "info",
            time.perf_counter(),
            "job",
            "time_accumulate",
            summary="job: fetch=1.0s total=2.0s",
            logger=logger,
        )

        assert logger.log.call_args[0][1] == "job: fetch=1.0s total=2.0s"

    def test_summary_replaces_the_error_message(self) -> None:
        logger = Mock()

        TimeExecutioner._log_execution(
            "info",
            time.perf_counter(),
            "job",
            "time_accumulate",
            error=ValueError("nope"),
            summary="job: total=2.0s error=ValueError: nope",
            logger=logger,
        )

        assert logger.error.call_args[0][0] == "job: total=2.0s error=ValueError: nope"

    def test_without_summary_the_success_message_is_unchanged(self) -> None:
        logger = Mock()

        TimeExecutioner._log_execution("info", time.perf_counter(), "f()", "C", logger=logger)

        assert "C.f(): executed in" in logger.log.call_args[0][1]

    def test_without_summary_the_error_message_is_unchanged(self) -> None:
        logger = Mock()

        TimeExecutioner._log_execution(
            "info",
            time.perf_counter(),
            "f()",
            "C",
            error=ValueError("nope"),
            logger=logger,
        )

        assert logger.error.call_args[0][0] == "Error in C.f(): nope"

    def test_summary_does_not_change_the_payload(self) -> None:
        logger = Mock()

        TimeExecutioner._log_execution(
            "info",
            time.perf_counter(),
            "job",
            "time_accumulate",
            summary="anything",
            logger=logger,
        )

        payload = logger.log.call_args[1]["extra"]
        assert payload["function_name"] == "job"
        assert payload["class_name"] == "time_accumulate"
        assert isinstance(payload["execution_time"], float)


class TestPhaseAccumulatorTotals:
    def test_same_label_accumulates_across_entries(self) -> None:
        acc = PhaseAccumulator("batch", Mock())

        for _ in range(3):
            with acc.time("fetch"):
                time.sleep(0.01)

        assert list(acc.phases) == ["fetch"]
        assert acc.phases["fetch"] >= 0.03

    def test_phases_are_ordered_by_first_entry(self) -> None:
        acc = PhaseAccumulator("batch", Mock())

        with acc.time("fetch"):
            pass
        with acc.time("write"):
            pass
        with acc.time("fetch"):
            pass

        assert list(acc.phases) == ["fetch", "write"]

    def test_counts_accumulate_and_default_to_one(self) -> None:
        acc = PhaseAccumulator("batch", Mock())

        acc.count("skipped")
        acc.count("skipped")
        acc.count("rejected", 10)

        assert acc.counts == {"skipped": 2, "rejected": 10}

    def test_counts_and_phases_are_separate_namespaces(self) -> None:
        acc = PhaseAccumulator("batch", Mock())

        with acc.time("x"):
            pass
        acc.count("x", 5)

        assert acc.counts["x"] == 5
        assert isinstance(acc.phases["x"], float)

    def test_snapshots_are_copies(self) -> None:
        acc = PhaseAccumulator("batch", Mock())
        acc.count("skipped")

        acc.counts["skipped"] = 999
        acc.phases["injected"] = 1.0

        assert acc.counts == {"skipped": 1}
        assert acc.phases == {}

    def test_a_phase_is_recorded_even_when_the_block_raises(self) -> None:
        acc = PhaseAccumulator("batch", Mock())

        def fail_inside_the_phase() -> None:
            with acc.time("fetch"):
                raise ValueError("nope")

        # The raise is the only thing in the block that should throw; if
        # time() itself threw instead, `match` would not line up.
        with pytest.raises(ValueError, match="nope"):
            fail_inside_the_phase()

        assert "fetch" in acc.phases

    def test_totals_are_exact_under_thread_contention(self) -> None:
        logger = Mock()
        acc = PhaseAccumulator("batch", logger)
        barrier = threading.Barrier(8)

        def worker() -> None:
            barrier.wait()
            for _ in range(500):
                with acc.time("work"):
                    pass
                acc.count("items")

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # A lost read-modify-write would show up here as a count below 4000.
        assert acc.counts == {"items": 4000}
        assert list(acc.phases) == ["work"]
        # Each thread has its own overlap stack, so concurrent same-label
        # blocks must not read as nesting.
        logger.warning.assert_not_called()


class TestPhaseAccumulatorOverlap:
    def test_nested_blocks_warn_once_naming_both_labels(self) -> None:
        logger = Mock()
        acc = PhaseAccumulator("batch", logger)

        with acc.time("outer"):
            with acc.time("inner"):
                pass

        logger.warning.assert_called_once()
        message = logger.warning.call_args[0][0]
        assert "inner" in message
        assert "outer" in message
        assert "unaccounted" in message

    def test_the_warning_does_not_repeat_per_iteration(self) -> None:
        logger = Mock()
        acc = PhaseAccumulator("batch", logger)

        for _ in range(100):
            with acc.time("outer"):
                with acc.time("inner"):
                    pass

        logger.warning.assert_called_once()

    def test_recursion_into_the_same_label_counts_as_overlap(self) -> None:
        logger = Mock()
        acc = PhaseAccumulator("batch", logger)

        with acc.time("fetch"):
            with acc.time("fetch"):
                pass

        logger.warning.assert_called_once()

    def test_sequential_blocks_do_not_warn(self) -> None:
        logger = Mock()
        acc = PhaseAccumulator("batch", logger)

        with acc.time("fetch"):
            pass
        with acc.time("write"):
            pass

        logger.warning.assert_not_called()

    def test_overlapping_blocks_still_accumulate_naively(self) -> None:
        acc = PhaseAccumulator("batch", Mock())

        with acc.time("outer"):
            with acc.time("inner"):
                time.sleep(0.01)

        # Both are charged the full elapsed time; nothing is subtracted.
        assert acc.phases["inner"] >= 0.01
        assert acc.phases["outer"] >= 0.01


class TestPhaseAccumulatorRendering:
    @staticmethod
    def _loaded() -> PhaseAccumulator:
        """An accumulator with fetch=315.200s, write=299.300s, skipped=12."""
        acc = PhaseAccumulator("weather-load", Mock())
        clock = [0.0, 315.2, 315.2, 614.5]
        with patch("time_executioner._accumulator.time.perf_counter", side_effect=clock):
            with acc.time("fetch"):
                pass
            with acc.time("write"):
                pass
        acc.count("skipped", 12)
        return acc

    def test_summary_matches_the_documented_shape(self) -> None:
        summary = self._loaded().summary(781.0)

        assert summary == (
            "weather-load: fetch=315.200s write=299.300s skipped=12 "
            "total=781.000s unaccounted=166.500s"
        )

    def test_summary_appends_the_error(self) -> None:
        summary = self._loaded().summary(781.0, ValueError("nope"))

        assert summary.endswith(" error=ValueError: nope")
        assert "unaccounted=166.500s" in summary

    def test_summary_of_an_empty_accumulator(self) -> None:
        acc = PhaseAccumulator("idle", Mock())

        assert acc.summary(2.0) == "idle: total=2.000s unaccounted=2.000s"

    def test_payload_keeps_full_precision(self) -> None:
        payload = self._loaded().payload(781.0)

        assert payload["phases"]["fetch"] == pytest.approx(315.2)
        assert payload["phases"]["write"] == pytest.approx(299.3)
        assert payload["counts"] == {"skipped": 12}
        assert payload["unaccounted"] == pytest.approx(166.5)

    def test_counts_never_enter_the_unaccounted_arithmetic(self) -> None:
        acc = self._loaded()
        before = acc.payload(781.0)["unaccounted"]

        acc.count("skipped", 1_000_000)

        assert acc.payload(781.0)["unaccounted"] == before


class TestAccumulate:
    def test_one_record_regardless_of_iteration_count(self, mock_logger: MagicMock) -> None:
        with TimeExecutioner.accumulate("batch") as phases:
            for _ in range(500):
                with phases.time("fetch"):
                    pass
                with phases.time("write"):
                    pass

        mock_logger.log.assert_called_once()

    def test_the_message_carries_the_breakdown(self, mock_logger: MagicMock) -> None:
        with TimeExecutioner.accumulate("batch") as phases:
            with phases.time("fetch"):
                pass
            phases.count("skipped", 3)

        message = mock_logger.log.call_args[0][1]
        assert message.startswith("batch: fetch=")
        assert "skipped=3" in message
        assert "total=" in message
        assert "unaccounted=" in message

    def test_payload_shape(self, mock_logger: MagicMock) -> None:
        with TimeExecutioner.accumulate("batch") as phases:
            with phases.time("fetch"):
                pass
            phases.count("skipped")

        payload = mock_logger.log.call_args[1]["extra"]
        assert payload["function_name"] == "batch"
        assert payload["class_name"] == "time_accumulate"
        assert isinstance(payload["execution_time"], float)
        assert payload["is_async"] is False  # matches time(), which leaves the default
        assert list(payload["phases"]) == ["fetch"]
        assert payload["counts"] == {"skipped": 1}
        assert isinstance(payload["unaccounted"], float)

    def test_the_record_closes_on_itself(self, mock_logger: MagicMock) -> None:
        with TimeExecutioner.accumulate("batch") as phases:
            with phases.time("fetch"):
                time.sleep(0.01)

        payload = mock_logger.log.call_args[1]["extra"]
        message = mock_logger.log.call_args[0][1]
        total = payload["execution_time"]

        # One wall-clock reading behind all three, so the arithmetic a reader
        # does on the payload matches what the message shows.
        assert f"total={total:.3f}s" in message
        assert payload["unaccounted"] == total - sum(payload["phases"].values())

    def test_caller_extra_wins_on_collision(self, mock_logger: MagicMock) -> None:
        with TimeExecutioner.accumulate("batch", extra={"counts": "mine", "run_id": 7}):
            pass

        payload = mock_logger.log.call_args[1]["extra"]
        assert payload["counts"] == "mine"
        assert payload["run_id"] == 7

    def test_log_level_is_honored(self, mock_logger: MagicMock) -> None:
        with TimeExecutioner.accumulate("batch", log_level="debug"):
            pass

        assert mock_logger.log.call_args[0][0] == logging.DEBUG

    def test_unaccounted_is_non_negative_on_a_serial_path(self, mock_logger: MagicMock) -> None:
        with TimeExecutioner.accumulate("batch") as phases:
            for _ in range(20):
                with phases.time("fetch"):
                    time.sleep(0.001)

        payload = mock_logger.log.call_args[1]["extra"]
        assert payload["unaccounted"] >= 0.0
        assert payload["unaccounted"] < payload["execution_time"]

    def test_empty_accumulator_still_flushes(self, mock_logger: MagicMock) -> None:
        with TimeExecutioner.accumulate("idle"):
            pass

        mock_logger.log.assert_called_once()
        assert mock_logger.log.call_args[1]["extra"]["phases"] == {}

    def test_exception_flushes_at_error_level_with_the_breakdown(self) -> None:
        mine = Mock()

        def fail_after_a_phase() -> None:
            with TimeExecutioner.accumulate("batch", logger=mine) as phases:
                with phases.time("fetch"):
                    pass
                raise ValueError("nope")

        with pytest.raises(ValueError, match="nope"):
            fail_after_a_phase()

        mine.error.assert_called_once()
        mine.log.assert_not_called()
        message = mine.error.call_args[0][0]
        assert "fetch=" in message
        assert "unaccounted=" in message
        assert message.endswith("error=ValueError: nope")
        assert mine.error.call_args[1]["extra"]["error"] == "nope"

    def test_partial_inner_block_is_recorded_when_it_raises(self) -> None:
        mine = Mock()

        def fail_mid_phase() -> None:
            with TimeExecutioner.accumulate("batch", logger=mine) as phases:
                with phases.time("fetch"):
                    raise ValueError("nope")

        with pytest.raises(ValueError, match="nope"):
            fail_mid_phase()

        assert "fetch" in mine.error.call_args[1]["extra"]["phases"]

    def test_per_use_logger_wins_over_the_global(self) -> None:
        theirs, mine = Mock(), Mock()
        TimeExecutioner.set_logger(theirs)

        with TimeExecutioner.accumulate("batch", logger=mine):
            pass

        mine.log.assert_called_once()
        theirs.log.assert_not_called()

    def test_the_overlap_warning_goes_to_the_same_logger(self) -> None:
        mine = Mock()

        with TimeExecutioner.accumulate("batch", logger=mine) as phases:
            with phases.time("outer"):
                with phases.time("inner"):
                    pass

        mine.warning.assert_called_once()

    def test_the_yielded_object_is_a_phase_accumulator(self, mock_logger: MagicMock) -> None:
        with TimeExecutioner.accumulate("batch") as phases:
            pass

        assert isinstance(phases, PhaseAccumulator)
