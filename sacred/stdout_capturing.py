#!/usr/bin/env python
# coding=utf-8

import os
import sys
import subprocess
import warnings
from io import StringIO
from contextlib import contextmanager
import wrapt
from sacred.optional import libc
from tempfile import NamedTemporaryFile
from sacred.settings import SETTINGS


def flush():
    """Try to flush all stdio buffers, both from python and from C."""
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except (AttributeError, ValueError, OSError):
        pass  # unsupported
    try:
        libc.fflush(None)
    except (AttributeError, ValueError, OSError):
        pass  # unsupported


def get_stdcapturer(mode=None):
    mode = mode if mode is not None else SETTINGS.CAPTURE_MODE
    capture_options = {"no": no_tee, "fd": tee_output_fd, "sys": tee_output_python}
    if mode not in capture_options:
        raise KeyError(
            "Unknown capture mode '{}'. Available options are {}".format(
                mode, sorted(capture_options.keys())
            )
        )
    return mode, capture_options[mode]


class TeeingStreamProxy(wrapt.ObjectProxy):
    """A wrapper around stdout or stderr that duplicates all output to out."""

    def __init__(self, wrapped, out):
        super().__init__(wrapped)
        self._self_out = out

    def write(self, data):
        self.__wrapped__.write(data)
        self._self_out.write(data)

    def flush(self):
        self.__wrapped__.flush()
        self._self_out.flush()


class CapturedStdout:
    def __init__(self, buffer):
        self.buffer = buffer
        self.read_position = 0
        self.final = None

    @property
    def closed(self):
        return self.buffer.closed

    def flush(self):
        return self.buffer.flush()

    def get(self):
        if self.final is None:
            self.buffer.seek(self.read_position)
            value = self.buffer.read()
            self.read_position = self.buffer.tell()
            return value
        else:
            value = self.final
            self.final = None
            return value

    def finalize(self):
        self.flush()
        self.final = self.get()
        self.buffer.close()


@contextmanager
def no_tee():
    out = CapturedStdout(StringIO())
    try:
        yield out
    finally:
        out.finalize()


@contextmanager
def tee_output_python():
    """Duplicate sys.stdout and sys.stderr to new StringIO."""
    buffer = StringIO()
    out = CapturedStdout(buffer)
    orig_stdout, orig_stderr = sys.stdout, sys.stderr
    flush()
    sys.stdout = TeeingStreamProxy(sys.stdout, buffer)
    sys.stderr = TeeingStreamProxy(sys.stderr, buffer)
    try:
        yield out
    finally:
        flush()
        out.finalize()
        sys.stdout, sys.stderr = orig_stdout, orig_stderr


# Duplicate stdout and stderr to a file. Inspired by:
# http://eli.thegreenplace.net/2015/redirecting-all-kinds-of-stdout-in-python/
# http://stackoverflow.com/a/651718/1388435
# http://stackoverflow.com/a/22434262/1388435
@contextmanager
def tee_output_fd():
    """Duplicate stdout and stderr to a file on the file descriptor level."""
    with NamedTemporaryFile(mode="w+", newline="") as target:
        original_stdout_fd = 1
        original_stderr_fd = 2
        target_fd = target.fileno()

        # Save a copy of the original stdout and stderr file descriptors)
        saved_stdout_fd = os.dup(original_stdout_fd)
        saved_stderr_fd = os.dup(original_stderr_fd)

        try:
            # start_new_session=True to move process to a new process group
            # this is done to avoid receiving KeyboardInterrupts (see #149)
            tee_stdout = subprocess.Popen(
                ["tee", "-a", target.name],
                start_new_session=True,
                stdin=subprocess.PIPE,
                stdout=1,
            )
            tee_stderr = subprocess.Popen(
                ["tee", "-a", target.name],
                start_new_session=True,
                stdin=subprocess.PIPE,
                stdout=2,
            )
        except (FileNotFoundError, OSError, AttributeError):
            # No tee found in this operating system. Trying to use a python
            # implementation of tee. However this is slow and error-prone.
            tee_stdout = subprocess.Popen(
                [sys.executable, "-m", "sacred.pytee"],
                stdin=subprocess.PIPE,
                stderr=target_fd,
            )
            tee_stderr = subprocess.Popen(
                [sys.executable, "-m", "sacred.pytee"],
                stdin=subprocess.PIPE,
                stdout=target_fd,
            )

        flush()
        os.dup2(tee_stdout.stdin.fileno(), original_stdout_fd)
        os.dup2(tee_stderr.stdin.fileno(), original_stderr_fd)
        out = CapturedStdout(target)

        try:
            yield out  # let the caller do their printing
        finally:
            flush()

            # then redirect stdout back to the saved fd
            tee_stdout.stdin.close()
            tee_stderr.stdin.close()

            # restore original fds
            os.dup2(saved_stdout_fd, original_stdout_fd)
            os.dup2(saved_stderr_fd, original_stderr_fd)

            try:
                tee_stdout.wait(timeout=1)
            except subprocess.TimeoutExpired:
                warnings.warn("tee_stdout.wait timeout. Forcibly terminating.")
                tee_stdout.terminate()

            try:
                tee_stderr.wait(timeout=1)
            except subprocess.TimeoutExpired:
                warnings.warn("tee_stderr.wait timeout. Forcibly terminating.")
                tee_stderr.terminate()

            os.close(saved_stdout_fd)
            os.close(saved_stderr_fd)
            out.finalize()
