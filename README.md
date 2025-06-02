# Time Executioner

A simple common decorator library for timing and logging function calls in python, including support for both sync and async function types. 

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
```

Which will result in automatic logging to the default logger:

```
my_cool_method_to_time() executed in 4.697 seconds
```

You can also provide specific logging levels in the decorator (`INFO` is the default) as a parameter passed into the decorator. 

```python
from time_executioner import TimeExecutioner

@TimeExecutioner.log(log_level="debug")
def my_cool_method_to_time():
    x = 2
    # ...
```

Or, if you'd like to provide a custom logger, that implements the logging.Logger, that is also supported:

```python
logger = MySuperCoolLogger()
TimeExecutioner.set_logger(logger)
```
