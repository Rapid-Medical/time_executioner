# Time Executioner

A simple common decorator and context manager library for timing and logging function calls in python,
including support for both sync and async function types.

Three ways in, depending on what you are timing:

| | Use it for | Logs |
| --- | --- | --- |
| `@TimeExecutioner.log` | a whole function, sync or async | one line per call |
| `TimeExecutioner.time(label)` | a block of code | one line per exit |
| `TimeExecutioner.accumulate(label)` | a phase inside a loop | one line per run, with a breakdown |

Requires Python 3.11+. Fully type annotated and ships a `py.typed` marker, so
`mypy` and other type checkers see the annotations in your project.

## Installation

```bash
pip install time_executioner
```

## Usage

To use the `TimeExecutioner` package you can simply use the python decorator features around your method.

### Example Code

```python
from time_executioner import TimeExecutioner


@TimeExecutioner.log
def my_cool_method_to_time():
    x = 2
    # ...


# no difference for async methods:
@TimeExecutioner.log
async def my_cool_async_method_to_time():
    x = 2
    # ...


# or you can use it as a context manager
with TimeExecutioner.time("my-expensive-codeblock"):
    y = 4
    # ...
```

Which will result in automatic logging to the default logger:

```
my_cool_method_to_time() executed in 0.697 seconds
my_cool_async_method_to_time() executed in 0.173 seconds
time_execute.my-expensive-codeblock executed in 2.401 seconds
```

### Timing a loop: `accumulate()`

`time()` logs on every context exit, which is wrong for code that times the same
phase across thousands of iterations — you get thousands of lines instead of one
summary. `accumulate()` adds up the phases and logs once:

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

One line on exit:

```
weather-load: fetch=315.200s write=299.300s skipped=12 total=781.000s unaccounted=166.500s
```

`unaccounted` is wall clock minus the sum of the phases — the time that went
somewhere you did not think to measure. It is usually the most useful number in
the line.

`count()` tallies are kept out of the seconds total on purpose: mixing them in
would corrupt `unaccounted`.

The structured breakdown also reaches the log record's `extra` payload, under
`phases`, `counts`, and `unaccounted`, at full precision. `phases` and `counts`
are readable from the accumulator too, if you want the numbers in your own
result object.

If an exception escapes the block, the summary is still logged — at error level,
with the breakdown intact — and the exception propagates. A run that dies still
tells you where its time went.

Two caveats. Nesting one `time()` block inside another charges both in full, so
`unaccounted` can go negative; the library warns once when it sees this. And
totals are additive across threads, so if worker threads time their own phases
the sum can exceed wall clock for the same reason. Accumulation itself is
thread-safe — the totals are lock-protected — it is the arithmetic of
"unaccounted" that assumes a serial path.

#### What `accumulate()` gives you

`TimeExecutioner.accumulate(label, log_level="info", extra=None, logger=None)` is
a context manager taking the same arguments as `time()`. It yields a
`PhaseAccumulator`:

| Member | Does |
| --- | --- |
| `phases.time(label)` | context manager; adds its elapsed wall clock to `label`'s running total. Reentrant — enter it ten thousand times and you get one figure |
| `phases.count(name, n=1)` | adds `n` to `name`'s running tally. Never enters the seconds total |
| `phases.phases` | snapshot `dict[str, float]` of accumulated seconds, ordered by first entry |
| `phases.counts` | snapshot `dict[str, int]` of accumulated counts |

On exit it logs exactly one record through the same path as the decorator and
`time()`, so a custom logger, `log_level`, and `extra` all behave the way they do
elsewhere in the library. The record carries:

| Payload key | Value |
| --- | --- |
| `function_name` | the accumulate label |
| `class_name` | `"time_accumulate"` |
| `execution_time` | wall clock for the whole block |
| `phases` | `{label: seconds}`, full precision |
| `counts` | `{name: count}` |
| `unaccounted` | wall clock minus the sum of the phases |

Your own `extra` merges last and wins on collision, so passing
`extra={"run_id": ...}` is safe and passing `extra={"phases": ...}` overrides.

`PhaseAccumulator` is importable for annotations:

```python
from time_executioner import PhaseAccumulator
```


You can also provide specific logging levels in the decorator (`INFO` is the default) as a parameter.

```python
from time_executioner import TimeExecutioner


@TimeExecutioner.log(log_level="debug")
def my_cool_method_to_time():
    x = 2
    # ...


# or as a context manager: 
with TimeExecutioner.time("my-expensive-codeblock", log_level="critical"):
    sleep(1)
```

And, finally, if you'd like to provide a custom logger, assuming that implements the logging.Logger, that is also
supported:

```python
logger = EliteCustomLogger()
TimeExecutioner.set_logger(logger)
```

`set_logger()` sets the default for the whole process, so the last caller wins. If you
are writing a library, or share a process with code you do not control, pass `logger=`
per use instead — it overrides the default without mutating it:

```python
from time_executioner import TimeExecutioner


@TimeExecutioner.log(logger=my_logger)
def my_cool_method_to_time():
    ...


with TimeExecutioner.time("my-expensive-codeblock", logger=my_logger):
    ...
```

`TimeExecutioner.reset_logger()` restores the built-in default, which is useful for
undoing a `set_logger()` call in test teardown.

