"""Accumulating phase timer: many timed blocks, one summary line."""

import threading
import time
from contextlib import contextmanager
from logging import Logger
from typing import Any, Generator


class PhaseAccumulator:
    """
    Accumulates per-phase wall clock and per-name counts for a single run.

    Handed out by `TimeExecutioner.accumulate()`. Every `time()` block adds to
    its label's running total rather than logging, so a loop that times the same
    phase ten thousand times produces one figure instead of ten thousand lines.

    Counts are deliberately a separate namespace from seconds: summing a count
    into the seconds total would corrupt the `unaccounted` figure, which is the
    number this class exists to produce.

    Mutation is lock-protected, so worker threads may time their own blocks
    without losing updates. Totals are additive across threads, so a threaded
    caller will see the phase sum exceed wall clock and `unaccounted` go
    negative; read that as "the phases overlapped", not as an error.
    """

    def __init__(self, label: str, logger: Logger) -> None:
        self._label = label
        self._logger = logger
        self._lock = threading.Lock()
        self._phases: dict[str, float] = {}
        self._counts: dict[str, int] = {}
        # Per-thread, so two workers inside the same phase are not mistaken
        # for recursion into it.
        self._local = threading.local()
        self._warned = False

    @property
    def phases(self) -> dict[str, float]:
        """A snapshot of accumulated seconds per label, ordered by first entry."""
        with self._lock:
            return dict(self._phases)

    @property
    def counts(self) -> dict[str, int]:
        """A snapshot of accumulated counts per name."""
        with self._lock:
            return dict(self._counts)

    @contextmanager
    def time(self, label: str) -> Generator[None, None, None]:
        """Time a block, adding its elapsed wall clock to `label`'s total."""
        with self._lock:
            # Claim the key on entry so `phases` is ordered by first entry
            # rather than by first completion.
            self._phases.setdefault(label, 0.0)

        stack = self._active
        if stack:
            self._warn_overlap(label, stack[-1])
        stack.append(label)
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            stack.pop()
            with self._lock:
                self._phases[label] += elapsed

    def count(self, name: str, n: int = 1) -> None:
        """Add `n` to `name`'s running count. Never enters the seconds total."""
        with self._lock:
            self._counts[name] = self._counts.get(name, 0) + n

    def _warn_overlap(self, inner: str, outer: str) -> None:
        """
        Warn once that phases overlap, at the moment it first happens.

        Once per accumulator, not once per occurrence: the whole point of this
        class is that a hot loop emits one line, and a warning per iteration
        would recreate the flood it exists to prevent.
        """
        with self._lock:
            if self._warned:
                return
            self._warned = True

        self._logger.warning(
            f"{self._label}: timing block {inner!r} opened inside {outer!r}; "
            f"overlapping phases are both charged in full, so 'unaccounted' may be negative"
        )

    def summary(self, wall: float, error: BaseException | None = None) -> str:
        """
        Render the one line this accumulator exists to produce.

        Seconds render at millisecond precision, matching the `.3f` the rest of
        the library logs; `payload()` carries the raw floats.
        """
        phases = self.phases
        parts = [f"{name}={seconds:.3f}s" for name, seconds in phases.items()]
        parts += [f"{name}={value}" for name, value in self.counts.items()]
        parts.append(f"total={wall:.3f}s")
        parts.append(f"unaccounted={wall - sum(phases.values()):.3f}s")

        line = f"{self._label}: {' '.join(parts)}"
        if error is not None:
            line = f"{line} error={type(error).__name__}: {error}"
        return line

    def payload(self, wall: float) -> dict[str, Any]:
        """
        The structured half of the same report, for the log record's `extra`.

        Nested dicts rather than flat `phase_fetch=` keys, so arbitrary user
        labels cannot collide with LogRecord attributes.
        """
        phases = self.phases
        return {
            "phases": phases,
            "counts": self.counts,
            "unaccounted": wall - sum(phases.values()),
        }

    @property
    def _active(self) -> list[str]:
        """This thread's stack of currently open phase labels."""
        stack: list[str] | None = getattr(self._local, "stack", None)
        if stack is None:
            stack = []
            self._local.stack = stack
        return stack
