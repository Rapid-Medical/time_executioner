# Accumulating timer for `time_executioner`

Date: 2026-08-19
Status: approved, ready for implementation planning

## Problem

`TimeExecutioner.time()` logs once per context exit. That fits a handful of
phases in one request. It does not fit code that times the same phase across
thousands of loop iterations: a batch job timing `fetch` and `write` per item
emits tens of thousands of log lines instead of one summary.

`rapid-data-warehouse`'s weather loader hand-rolled exactly this pattern in
`services/weather_loader/weather_loader/runner.py` because the library had no
accumulating variant. That instrumentation is what located the real bottleneck
after three wrong theories, so the pattern has earned its place in the library
rather than being copy-pasted per service.

## Goals

- One log line on exit, not per iteration, through the existing
  `_log_execution` path and `extra` payload convention.
- Report an unaccounted figure (wall clock minus the sum of phases). It is the
  number that reveals a phase nobody thought to time.
- Nestable inner blocks, reentrant for the same label: each entry adds to that
  label's total.
- Counters alongside timers, kept out of the seconds total so they cannot
  corrupt the unaccounted figure.
- Flush on exception, so a run that dies still reports where its time went.
- Zero runtime dependencies. `requires-python >= 3.11`, consistent with the
  package.

## Non-goals

- Per-thread timing breakdowns. See "Concurrency" for why they do not produce a
  better number. Adding them later is purely additive.
- An async-specific API. A synchronous `with` block measures wall clock
  correctly around `await` expressions; concurrent tasks are the same overlap
  problem as threads and are covered by the same caveat.
- Any change to the behavior of `TimeExecutioner.log()` or
  `TimeExecutioner.time()`.

## Public API

```python
with TimeExecutioner.accumulate("weather-load") as phases:
    for cell in cells:
        with phases.time("fetch"):
            data = fetch(cell)
        with phases.time("write"):
            write(data)
        if data is None:
            phases.count("skipped")
```

### `TimeExecutioner.accumulate`

```python
@staticmethod
@contextmanager
def accumulate(
    label: str,
    log_level: str = "info",
    extra: dict[str, Any] | None = None,
    logger: Logger | None = None,
) -> Generator["PhaseAccumulator", None, None]:
```

The signature matches `TimeExecutioner.time()` exactly, including the
`@staticmethod @contextmanager` pairing, so the two read as siblings.

### `PhaseAccumulator`

Exported from the `time_executioner` package so consumers can annotate against
it. Members:

- `time(label: str)` — a context manager. On exit, adds the elapsed wall clock
  to `label`'s running total.
- `count(name: str, n: int = 1) -> None` — adds `n` to `name`'s running count.
- `phases` — a read-only snapshot (a copy) of the accumulated seconds per label.
- `counts` — a read-only snapshot (a copy) of the accumulated counts per name.

The snapshot properties exist because the motivating code folds phase timings
into its own result object alongside logging them. Without accessors, the only
way for a caller to read its own numbers is to parse a log line.

Phase names and count names are separate namespaces. `time("x")` and
`count("x")` may coexist; the message disambiguates by the `s` suffix on
seconds, and the payload keeps them in separate dicts.

## Semantics

### Accumulation

Reentrant per label: each entry adds to that label's total. A `fetch` block
entered 10,000 times produces one `fetch` figure.

Accumulation is naive — every entry charges its full elapsed time to its own
label, with no subtraction of nested children.

### Overlap detection

Entering a `time()` block while the current thread's active-block stack is
non-empty is an overlap: either a nested inner block or recursion into the same
label. Under naive accumulation, overlapping blocks double-charge, which can
drive `unaccounted` negative.

On the first overlap only, one WARNING is emitted naming the pair (inner label
and the enclosing label) and stating that overlapping totals can make
`unaccounted` negative. It is emitted at the moment of the overlap rather than
deferred to the flush, so it points at the code that caused it. The accumulator
receives the already-resolved `Logger` at construction and calls `.warning()` on
it directly; it does not go through `_log_execution`. One warning per
`PhaseAccumulator` instance, not per occurrence — a loop that nests would
otherwise spray a warning per iteration, which is the exact failure this feature
exists to avoid.

Accumulation behavior is unchanged by the warning. A negative `unaccounted` is a
visible signal that phases overlapped, not a hidden error.

### Unaccounted

```
unaccounted = wall_clock - sum(phases.values())
```

Counts never enter this arithmetic.

### Exception path

Exit flushes exactly one record whether or not an exception is in flight. On an
exception the record goes out at ERROR with the full breakdown plus an error
suffix, and the exception propagates unchanged.

This deliberately diverges from `TimeExecutioner.time()`, which never escalates
log level on exception. The rationale is that the accumulator's whole purpose is
diagnosing long batch runs, and a run that dies is precisely when the breakdown
matters most.

An exception raised inside an inner `time()` block unwinds that block's context
manager first, so its partial elapsed time is accumulated before the flush.

## Concurrency

Mutation of the seconds and counts totals is protected by a `threading.Lock`.
`totals[label] += elapsed` is a read-modify-write; without the lock two threads
can silently lose an update. A timing tool that quietly reports a wrong number
is worse than one that reports nothing, and an uncontended lock costs tens of
nanoseconds — noise next to the two `perf_counter()` calls it guards.

The active-block stack used for overlap detection is thread-local. Shared, two
workers both inside `fetch` would look like recursive nesting and trigger a
spurious warning.

The `phases` and `counts` snapshot properties copy under the same lock, so a
caller reading them while workers are still timing gets a consistent snapshot
rather than a dict mutated mid-iteration.

Totals are additive across threads. A threaded caller will therefore see the sum
of phases exceed wall clock and `unaccounted` go negative. This is documented in
the docstring as the signal that phases overlapped.

Per-thread breakdowns were considered and rejected: `unaccounted` is only
meaningful on a serial path, and partitioning by thread does not repair that
invariant — it splits the same arithmetic into more columns while forcing a much
larger log payload.

## Log output

### Message

```
weather-load: fetch=315.200s write=299.300s skipped=12 total=781.000s unaccounted=166.500s
```

Ordering: phases in first-timed order, then counts in first-counted order, then
`total`, then `unaccounted`. Seconds render with `.3f` and carry an `s` suffix;
counts render as bare integers.

On the error path the same line gains an ` error=ValueError: boom` suffix
(exception class name and `str(exception)`) and is emitted via `logger.error`.

`.3f` matches the precision the decorator and `time()` already log at, so a
sub-second phase stays readable. The `extra` payload carries the raw floats for
anything that needs more.

`_log_execution` derives `execution_time` from `start_time` a few microseconds
after the accumulator takes its own wall-clock reading to build the string. Left
alone, that leaves the record not closing on itself: `execution_time` minus the
phase sum would not equal the reported `unaccounted`. `accumulate()` therefore
overrides `execution_time` in the payload with the same `wall` the message used,
relying on the documented rule that the passed payload wins over the keys
`_log_execution` generates.

### `_log_execution` change

`_log_execution` gains one optional parameter:

```python
summary: str | None = None
```

When set, `summary` is the message body in both the success branch and the error
branch. When `None` — which is every existing call site — behavior is
byte-identical to today, including the `Error in {class_name}.{func_name}:`
prefix on the error branch.

The accumulator builds the complete string, error suffix included, so
`_log_execution` remains a passthrough with no knowledge of phase formatting.

### `extra` payload

The accumulator passes:

```python
{
    "phases": {"fetch": 315.2408, "write": 299.3311},
    "counts": {"skipped": 12},
    "unaccounted": 166.5281,
}
```

`unaccounted` carries full float precision in the payload, like the per-phase
values; only the message rounds.

merged into the payload `_log_execution` already builds, where
`function_name` is the accumulate label, `class_name` is `"time_accumulate"`
(paralleling `"time_execute"` for `time()`), and `execution_time` is the wall
clock. `is_async` is left at the existing default, matching `time()`.

Caller-supplied `extra` merges last and wins on collision, preserving the
existing `payload | extra` convention.

Nested dicts are used rather than flat `phase_fetch=` keys so that arbitrary
user labels cannot collide with `LogRecord` attributes.

## Code layout

New module `src/time_executioner/_accumulator.py` holds `PhaseAccumulator`. It
accumulates, renders its own summary string, and emits the overlap warning
through the `Logger` handed to it at construction. It has no knowledge of
`_log_execution`, log levels, or payload assembly: `_core.accumulate()` resolves
the logger, constructs the accumulator, and performs the flush.

The dependency runs one way, `_core` -> `_accumulator`, so there is no circular
import, and `_core.py` does not grow another 120 lines.

`PhaseAccumulator` is re-exported from `src/time_executioner/__init__.py` and
added to `__all__`.

Zero new runtime dependencies: `threading` and `contextlib` are stdlib.

## Testing

Test-driven, in the existing suite's style (`caplog` and `Mock` loggers,
`patch` on `perf_counter` where exact numbers are asserted).

Coverage:

1. Exactly one log record on exit, regardless of iteration count.
2. Reentrancy: the same label entered N times sums to the total of N elapsed
   spans.
3. Counts are excluded from the seconds total and from `unaccounted`.
4. `unaccounted` equals wall clock minus the phase sum, and is non-negative in
   serial, non-overlapping use.
5. Exception path: one record, ERROR level, breakdown present in the message,
   error suffix present, exception propagates.
6. Message format matches the documented shape, including ordering and the `s`
   suffix.
7. `extra` payload shape, and caller-supplied `extra` winning on collision.
8. `logger=` per-use override and `set_logger()` process default both honored.
9. `log_level` honored on the success path.
10. Overlap warning fires exactly once per accumulator, not once per iteration.
11. Threaded test: N threads times M increments produces exact totals under
    contention.
12. Empty accumulator (no phases, no counts) still flushes one record.
13. Regression: `_log_execution` with `summary=None` produces unchanged output
    on both the success and error branches.

## Documentation

- README section covering `accumulate()`, the unaccounted figure, counters, and
  the cross-thread caveat.
- CHANGELOG entry under `## [Unreleased]` -> `### Added`.
- A line in `describe()` in `__init__.py`.

`__version__` stays at `0.1.0`; the release CI bumps on tag, so bumping here is
part of releasing rather than part of this change.

## Decisions already closed

| Question | Decision |
| --- | --- |
| Message shape | Extend `_log_execution` with a `summary` override |
| Overlapping labels | Naive accumulation, one warning per accumulator on overlap |
| Exception flush | ERROR level with the breakdown, exception propagates |
| Concurrency | Lock-protected shared totals, thread-local overlap stack |

## Already fixed, no action needed

Both items raised alongside this feature landed in commit 2380641 ("correct
packaging, publish type information, and close CI gaps before first release"):

- `tests/test_time_executioner.py` already imports `from time_executioner import
  TimeExecutioner`, and `pyproject.toml` carries
  `[tool.setuptools.packages.find] where = ["src"]` against a real
  `src/time_executioner/` package.
- The `Homepage` URL is correct; the typo fix is recorded in the 0.1.0 CHANGELOG
  entry.
