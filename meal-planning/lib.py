
import contextlib
import io
import sys

class MultiWriter(io.TextIOBase):
    def __init__(self, *streams):
        self._streams = streams

    def close(self):
        raise IOError()

    def closed(self):
        return False

    def fileno(self):
        raise IOError()

    def flush(self):
        for s in self._streams:
            s.flush()

    def isatty(self):
        return False

    def readable(self):
        return False

    def seekable(self):
        return False

    def tell(self):
        raise IOError()

    def truncate(self):
        raise IOError()

    def writable(self):
        return True

    def write(self, s):
        result = 0
        for x in self._streams:
            result = x.write(s)
        return result


@contextlib.contextmanager
def tee(*streams):
    old_stdout = sys.stdout
    try:
        sys.stdout = MultiWriter(sys.stdout, *streams)
        yield
    finally:
        sys.stdout = old_stdout

