# Usage

To use the `TimeExecutioner` package you can simply use the python decorator
features around your method.

## Example Code

```python
from src import TimeExecutioner


@TimeExecutioner.log
def my_cool_method_to_time():
    x = 2
    # ...
```

Which will result in automatic logging to the default logger:

```
my_cool_method_to_time() executed in 4.697 seconds
```

You can also provide specific logging levels in the decorator (`INFO` is the default):

```python
from src import TimeExecutioner


@TimeExecutioner.log(log_level="debug")
def my_cool_method_to_time():
    x = 2
    # ...
```

Or, if you'd like to provide a custom logger, that implements the logging.Logger, that is also supported:

```python
from src import TimeExecutioner

logger = MySuperCoolLogger()
TimeExecutioner.set_logger(logger)
```