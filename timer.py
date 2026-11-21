import time
from contextlib import contextmanager

def format_duration(seconds):
    if seconds < 1e-6:                         # < 1 microsecond
        return f"{seconds * 1e9:.0f} ns"
    if seconds < 1e-3:                         # < 1 millisecond
        return f"{seconds * 1e6:.1f} μs"
    if seconds < 1:                            # < 1 second
        return f"{seconds * 1000:.2f} ms"
    if seconds < 60:
        return f"{seconds:.2f} s"
    m, s = divmod(seconds, 60)
    return f"{int(m)}m {s:.1f}s"


@contextmanager
def timer(label="", verbose=True):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - t0
        if verbose:
            print(f"{label:<16}: {format_duration(elapsed)}")
            print("-" * 40)
            