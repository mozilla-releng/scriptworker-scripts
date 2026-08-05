import os
from pathlib import Path

TEST_DATA_DIR = Path(os.path.dirname(__file__)) / "data"


def fake_redo_retry(func, args, kwargs, *retry_args, **retry_kwargs):
    """Mock redo.retry; can also get around @redo.retriable decorator."""
    return func(*args, **kwargs)
