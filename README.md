# Time Executioner

A simple common decorator and context manager library for timing and logging function calls in python,
including support for both sync and async function types.

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

