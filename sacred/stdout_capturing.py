#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import os
import sys
import subprocess
from threading import Timer
from contextlib import contextmanager
import wrapt
from sacred.optional import libc
from tempfile import NamedTemporaryFile
from sacred.settings import SETTINGS
from sacred.utils import FileNotFoundError, StringIO


def flush():
    """Try to flush all stdio buffers, both from python and from C."""
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except (AttributeError, ValueError, IOError):
        pass  # unsupported
    try:
        libc.fflush(None)
    except (AttributeError, ValueError, IOError):
        pass  # unsupported


def get_stdcapturer(mode=None):
    mode = mode if mode is not None else SETTINGS.CAPTURE_MODE
    return mode, {
        "no": no_tee,
        "fd": tee_output_fd,
        "sys": tee_output_python}[mode]


class TeeingStreamProxy(wrapt.ObjectProxy):
    """A wrapper around stdout or stderr that duplicates all output to out."""

    def __init__(self, wrapped, out):
        super(TeeingStreamProxy, self).__init__(wrapped)
        self._self_out = out

    def write(self, data):
        self.__wrapped__.write(data)
        self._self_out.write(data)

    def flush(self):
        self.__wrapped__.flush()
        self._self_out.flush()


class CapturedStdout(object):
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
    with NamedTemporaryFile(mode='w+') as target:
        original_stdout_fd = 1
        original_stderr_fd = 2
        target_fd = target.fileno()

        # Save a copy of the original stdout and stderr file descriptors
        saved_stdout_fd = os.dup(original_stdout_fd)
        saved_stderr_fd = os.dup(original_stderr_fd)

        try:
            # we call os.setsid to move process to a new process group
            # this is done to avoid receiving KeyboardInterrupts (see #149)
            # in Python 3 we could just pass start_new_session=True
            tee_stdout = subprocess.Popen(
                ['tee', '-a', '/dev/stderr'], preexec_fn=os.setsid,
                stdin=subprocess.PIPE, stderr=target_fd, stdout=1)
            tee_stderr = subprocess.Popen(
                ['tee', '-a', '/dev/stderr'], preexec_fn=os.setsid,
                stdin=subprocess.PIPE, stderr=target_fd, stdout=2)
        except (FileNotFoundError, (OSError, AttributeError)):
            # No tee found in this operating system. Trying to use a python
            # implementation of tee. However this is slow and error-prone.
            tee_stdout = subprocess.Popen(
                [sys.executable, "-m", "sacred.pytee"],
                stdin=subprocess.PIPE, stderr=target_fd)
            tee_stderr = subprocess.Popen(
                [sys.executable, "-m", "sacred.pytee"],
                stdin=subprocess.PIPE, stdout=target_fd)

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

            # wait for completion of the tee processes with timeout
            # implemented using a timer because timeout support is py3 only
            def kill_tees():
                tee_stdout.kill()
                tee_stderr.kill()

            tee_timer = Timer(1, kill_tees)
            try:
                tee_timer.start()
                tee_stdout.wait()
                tee_stderr.wait()
            finally:
                tee_timer.cancel()

            os.close(saved_stdout_fd)
            os.close(saved_stderr_fd)
            out.finalize()
