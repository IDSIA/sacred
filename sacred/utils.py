#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import collections
import ctypes
import io
import logging
import os.path
import re
import subprocess
import sys
import tempfile
import traceback as tb
from contextlib import contextmanager

from io import StringIO
import wrapt

__sacred__ = True  # marks files that should be filtered from stack traces

NO_LOGGER = logging.getLogger('ignore')
NO_LOGGER.disabled = 1

PATHCHANGE = object()

PYTHON_IDENTIFIER = re.compile("^[a-zA-Z_][_a-zA-Z0-9]*$")

libc = ctypes.CDLL(None)
c_stdout = ctypes.c_void_p.in_dll(libc, 'stdout')
c_stderr = ctypes.c_void_p.in_dll(libc, 'stderr')


class CircularDependencyError(Exception):
    """The ingredients of the current experiment form a circular dependency."""


class ObserverError(Exception):
    """Error that an observer raises but that should not make the run fail."""


class TimeoutInterrupt(Exception):

    """Signal a that the experiment timed out.

    This exception can be used in client code to indicate that the run
    exceeded its time limit and has been interrupted because of that.
    """


def create_basic_stream_logger():
    logger = logging.getLogger('')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def recursive_update(d, u):
    """
    Given two dictionaries d and u, update dict d recursively.

    E.g.:
    d = {'a': {'b' : 1}}
    u = {'c': 2, 'a': {'d': 3}}
    => {'a': {'b': 1, 'd': 3}, 'c': 2}
    """
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = recursive_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


class Tee(object):
    def __init__(self, out1, out2):
        for attr in ['encoding', 'errors', 'name', 'mode', 'closed',
                     'line_buffering', 'newlines', 'softspace']:
            setattr(self, attr, getattr(out1, attr, None))
        self.out1 = out1
        self.out2 = out2

    def write(self, data):
        self.out1.write(data)
        self.out2.write(data)

    def flush(self):
        self.out1.flush()
        self.out2.flush()


def flush():
    libc.fflush(c_stdout)
    libc.fflush(c_stderr)
    sys.stdout.flush()
    sys.stderr.flush()


@contextmanager
def tee_output():
    try:
        original_stdout_fd = sys.stdout.fileno()  # The original fd stdout points to. Usually 1 on POSIX systems.
        original_stderr_fd = sys.stderr.fileno()  # The original fd stderr points to. Usually 2 on POSIX systems.
    except (io.UnsupportedOperation, AttributeError):
        original_stdout_fd = 1
        original_stderr_fd = 2

    # Save a copy of the original stdout and stderr file descriptors
    saved_stdout_fd = os.dup(original_stdout_fd)
    saved_stderr_fd = os.dup(original_stderr_fd)

    try:
        # Create a temporary file and redirect stdout to it
        with tempfile.NamedTemporaryFile('wb', delete=False) as tfile:
            try:
                tee_stdout = subprocess.Popen(['tee', '-a', tfile.name], stdin=subprocess.PIPE)
                tee_stderr = subprocess.Popen(['tee', '-a', tfile.name], stdin=subprocess.PIPE, stdout=saved_stderr_fd)
            except FileNotFoundError:
                tee_stdout = subprocess.Popen([sys.executable, "-m", "sacred.pytee"], stdin=subprocess.PIPE,
                                              stderr=tfile.fileno())
                tee_stderr = subprocess.Popen([sys.executable, "-m", "sacred.pytee"], stdin=subprocess.PIPE,
                                              stdout=tfile.fileno())

            flush()
            os.dup2(tee_stdout.stdin.fileno(), original_stdout_fd)
            os.dup2(tee_stderr.stdin.fileno(), original_stderr_fd)

            # Yield to caller, then redirect stdout back to the saved fd
            yield tfile

            flush()
            tee_stdout.stdin.close()
            tee_stderr.stdin.close()

            # restore original fds
            os.dup2(saved_stdout_fd, original_stdout_fd)
            os.dup2(saved_stderr_fd, original_stderr_fd)

        tee_stdout.wait()
        tee_stderr.wait()

    finally:
        os.close(saved_stdout_fd)
        os.close(saved_stderr_fd)


def iterate_flattened_separately(dictionary):
    """
    Recursively iterate over the items of a dictionary in a special order.

    First iterate over all items that are non-dictionary values
    (sorted by keys), then over the rest (sorted by keys), providing full
    dotted paths for every leaf.
    """
    single_line_keys = [key for key in dictionary.keys() if
                        not dictionary[key] or
                        not isinstance(dictionary[key], dict)]
    for key in sorted(single_line_keys):
        yield key, dictionary[key]

    multi_line_keys = [key for key in dictionary.keys()
                       if (dictionary[key] and
                           isinstance(dictionary[key], dict))]
    for key in sorted(multi_line_keys):
        yield key, PATHCHANGE
        for k, val in iterate_flattened_separately(dictionary[key]):
            yield join_paths(key, k), val


def iterate_flattened(d):
    """
    Recursively iterate over the items of a dictionary.

    Provides a full dotted paths for every leaf.
    """
    for key in sorted(d.keys()):
        value = d[key]
        if isinstance(value, dict):
            for k, v in iterate_flattened(d[key]):
                yield join_paths(key, k), v
        else:
            yield key, value


def set_by_dotted_path(d, path, value):
    """
    Set an entry in a nested dict using a dotted path.

    Will create dictionaries as needed.

    Examples:
    >>> d = {'foo': {'bar': 7}}
    >>> set_by_dotted_path(d, 'foo.bar', 10)
    >>> d
    {'foo': {'bar': 10}}
    >>> set_by_dotted_path(d, 'foo.d.baz', 3)
    >>> d
    {'foo': {'bar': 10, 'd': {'baz': 3}}}
    """
    split_path = path.split('.')
    current_option = d
    for p in split_path[:-1]:
        if p not in current_option:
            current_option[p] = dict()
        current_option = current_option[p]
    current_option[split_path[-1]] = value


def get_by_dotted_path(d, path):
    """
    Get an entry from nested dictionaries using a dotted path.

    Example:
    >>> get_by_dotted_path({'foo': {'a': 12}}, 'foo.a')
    12
    """
    if not path:
        return d
    split_path = path.split('.')
    current_option = d
    for p in split_path:
        if p not in current_option:
            return None
        current_option = current_option[p]
    return current_option


def iter_path_splits(path):
    """
    Iterate over possible splits of a dotted path.

    The first part can be empty the second should not be.

    Example:
    >>> list(iter_path_splits('foo.bar.baz'))
    [('',        'foo.bar.baz'),
     ('foo',     'bar.baz'),
     ('foo.bar', 'baz')]
    """
    split_path = path.split('.')
    for i in range(len(split_path)):
        p1 = join_paths(*split_path[:i])
        p2 = join_paths(*split_path[i:])
        yield p1, p2


def iter_prefixes(path):
    """
    Iterate through all (non-empty) prefixes of a dotted path.

    Example:
    >>> list(iter_prefixes('foo.bar.baz'))
    ['foo', 'foo.bar', 'foo.bar.baz']
    """
    split_path = path.split('.')
    for i in range(1, len(split_path) + 1):
        yield join_paths(*split_path[:i])


def join_paths(*parts):
    """Join different parts together to a valid dotted path."""
    return '.'.join(p.strip('.') for p in parts if p)


def is_prefix(pre_path, path):
    """Return True if pre_path is a path-prefix of path."""
    pre_path = pre_path.strip('.')
    path = path.strip('.')
    return not pre_path or path.startswith(pre_path + '.')


def convert_to_nested_dict(dotted_dict):
    """Convert a dict with dotted path keys to corresponding nested dict."""
    nested_dict = {}
    for k, v in iterate_flattened(dotted_dict):
        set_by_dotted_path(nested_dict, k, v)
    return nested_dict


def print_filtered_stacktrace():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    # determine if last exception is from sacred
    current_tb = exc_traceback
    while current_tb.tb_next is not None:
        current_tb = current_tb.tb_next
    if '__sacred__' in current_tb.tb_frame.f_globals:
        print("Exception originated from within Sacred.\n"
              "Traceback (most recent calls):", file=sys.stderr)
        tb.print_tb(exc_traceback)
        tb.print_exception(exc_type, exc_value, None)
    else:
        print("Traceback (most recent calls WITHOUT Sacred internals):",
              file=sys.stderr)
        current_tb = exc_traceback
        while current_tb is not None:
            if '__sacred__' not in current_tb.tb_frame.f_globals:
                tb.print_tb(current_tb, 1)
            current_tb = current_tb.tb_next
        print("\n".join(tb.format_exception_only(exc_type, exc_value)).strip(),
              file=sys.stderr)


def is_subdir(path, directory):
    path = os.path.abspath(os.path.realpath(path)) + os.sep
    directory = os.path.abspath(os.path.realpath(directory)) + os.sep

    return path.startswith(directory)


@wrapt.decorator
def optional_kwargs_decorator(wrapped, instance=None, args=None, kwargs=None):
    def _decorated(func):
        return wrapped(func, **kwargs)

    if args:
        return _decorated(*args)
    else:
        return _decorated


def get_inheritors(cls):
    """Get a set of all classes that inherit from the given class."""
    subclasses = set()
    work = [cls]
    while work:
        parent = work.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                work.append(child)
    return subclasses


# Credit to Zarathustra and epost from stackoverflow
# Taken from http://stackoverflow.com/a/1176023/1388435
def convert_camel_case_to_snake_case(name):
    """Convert CamelCase to snake_case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
