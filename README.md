# Time Executioner

A simple common decorator library for timing and logging function calls in python.

## Example Code

```python
from src import TimeExecutioner


@TimeExecutioner.log
def my_cool_method_to_time():
    x = 2
    # ...
```

