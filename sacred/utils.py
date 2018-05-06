#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import collections
import inspect
import logging
import os.path
import pkgutil
import re
import shlex
import sys
import threading
import traceback as tb
from functools import partial

import wrapt


__all__ = ["NO_LOGGER", "PYTHON_IDENTIFIER", "CircularDependencyError",
           "ObserverError", "SacredInterrupt", "TimeoutInterrupt",
           "create_basic_stream_logger", "recursive_update",
           "iterate_flattened", "iterate_flattened_separately",
           "set_by_dotted_path", "get_by_dotted_path", "iter_path_splits",
           "iter_prefixes", "join_paths", "is_prefix",
           "convert_to_nested_dict", "convert_camel_case_to_snake_case",
           "print_filtered_stacktrace", "is_subdir",
           "optional_kwargs_decorator", "get_inheritors",
           "apply_backspaces_and_linefeeds", "StringIO", "FileNotFoundError"]

# A PY2 compatible basestring, int_types and FileNotFoundError
if sys.version_info[0] == 2:
    basestring = basestring
    int_types = (int, long)

    import errno

    class FileNotFoundError(IOError):
        def __init__(self, msg):
            super(FileNotFoundError, self).__init__(errno.ENOENT, msg)
    from StringIO import StringIO
else:
    basestring = str
    int_types = (int,)

    # Reassign so that we can import it from here
    FileNotFoundError = FileNotFoundError
    from io import StringIO


NO_LOGGER = logging.getLogger('ignore')
NO_LOGGER.disabled = 1

PATHCHANGE = object()

PYTHON_IDENTIFIER = re.compile("^[a-zA-Z_][_a-zA-Z0-9]*$")


class CircularDependencyError(Exception):
    """The ingredients of the current experiment form a circular dependency."""


class ObserverError(Exception):
    """Error that an observer raises but that should not make the run fail."""


class SacredInterrupt(Exception):
    """Base-Class for all custom interrupts.

    For more information see :ref:`custom_interrupts`.
    """

    STATUS = "INTERRUPTED"


class TimeoutInterrupt(SacredInterrupt):
    """Signal a that the experiment timed out.

    This exception can be used in client code to indicate that the run
    exceeded its time limit and has been interrupted because of that.
    The status of the interrupted run will then be set to ``TIMEOUT``.

    For more information see :ref:`custom_interrupts`.
    """

    STATUS = "TIMEOUT"


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


def iterate_flattened_separately(dictionary, manually_sorted_keys=None):
    """
    Recursively iterate over the items of a dictionary in a special order.

    First iterate over manually sorted keys and then over all items that are
    non-dictionary values (sorted by keys), then over the rest
    (sorted by keys), providing full dotted paths for every leaf.
    """
    if manually_sorted_keys is None:
        manually_sorted_keys = []
    for key in manually_sorted_keys:
        if key in dictionary:
            yield key, dictionary[key]

    single_line_keys = [key for key in dictionary.keys() if
                        key not in manually_sorted_keys and
                        (not dictionary[key] or
                         not isinstance(dictionary[key], dict))]
    for key in sorted(single_line_keys):
        yield key, dictionary[key]

    multi_line_keys = [key for key in dictionary.keys() if
                       key not in manually_sorted_keys and
                       (dictionary[key] and
                        isinstance(dictionary[key], dict))]
    for key in sorted(multi_line_keys):
        yield key, PATHCHANGE
        for k, val in iterate_flattened_separately(dictionary[key],
                                                   manually_sorted_keys):
            yield join_paths(key, k), val


def iterate_flattened(d):
    """
    Recursively iterate over the items of a dictionary.

    Provides a full dotted paths for every leaf.
    """
    for key in sorted(d.keys()):
        value = d[key]
        if isinstance(value, dict) and value:
            for k, v in iterate_flattened(d[key]):
                yield join_paths(key, k), v
        else:
            yield key, value


def set_by_dotted_path(d, path, value):
    """
    Set an entry in a nested dict using a dotted path.

    Will create dictionaries as needed.

    Examples
    --------
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


def get_by_dotted_path(d, path, default=None):
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
            return default
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
    return '.'.join(str(p).strip('.') for p in parts if p)


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


def _is_sacred_frame(frame):
    return frame.f_globals["__name__"].split('.')[0] == 'sacred'


def print_filtered_stacktrace():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    # determine if last exception is from sacred
    current_tb = exc_traceback
    while current_tb.tb_next is not None:
        current_tb = current_tb.tb_next
    if _is_sacred_frame(current_tb.tb_frame):
        header = ["Exception originated from within Sacred.\n"
                  "Traceback (most recent calls):\n"]
        texts = tb.format_exception(exc_type, exc_value, current_tb)
        print(''.join(header + texts[1:]).strip(), file=sys.stderr)
    else:
        if sys.version_info >= (3, 3):
            tb_exception =\
                tb.TracebackException(exc_type, exc_value, exc_traceback,
                                      limit=None)
            for line in filtered_traceback_format(tb_exception):
                print(line, file=sys.stderr, end="")
        else:
            print("Traceback (most recent calls WITHOUT Sacred internals):",
                  file=sys.stderr)
            current_tb = exc_traceback
            while current_tb is not None:
                if not _is_sacred_frame(current_tb.tb_frame):
                    tb.print_tb(current_tb, 1)
                current_tb = current_tb.tb_next
            print("\n".join(tb.format_exception_only(exc_type,
                                                     exc_value)).strip(),
                  file=sys.stderr)


def filtered_traceback_format(tb_exception, chain=True):
    if chain:
        if tb_exception.__cause__ is not None:
            for line in filtered_traceback_format(tb_exception.__cause__,
                                                  chain=chain):
                yield line
            yield tb._cause_message
        elif (tb_exception.__context__ is not None and
              not tb_exception.__suppress_context__):
            for line in filtered_traceback_format(tb_exception.__context__,
                                                  chain=chain):
                yield line
            yield tb._context_message
    yield 'Traceback (most recent calls WITHOUT Sacred internals):\n'
    current_tb = tb_exception.exc_traceback
    while current_tb is not None:
        if not _is_sacred_frame(current_tb.tb_frame):
            stack = tb.StackSummary.extract(tb.walk_tb(current_tb),
                                            limit=1,
                                            lookup_lines=True,
                                            capture_locals=False)
            for line in stack.format():
                yield line
        current_tb = current_tb.tb_next
    for line in tb_exception.format_exception_only():
        yield line


def is_subdir(path, directory):
    path = os.path.abspath(os.path.realpath(path)) + os.sep
    directory = os.path.abspath(os.path.realpath(directory)) + os.sep

    return path.startswith(directory)


# noinspection PyUnusedLocal
@wrapt.decorator
def optional_kwargs_decorator(wrapped, instance=None, args=None, kwargs=None):
    # here wrapped is itself a decorator
    if args:  # means it was used as a normal decorator (so just call it)
        return wrapped(*args, **kwargs)
    else:  # used with kwargs, so we need to return a decorator
        return partial(wrapped, **kwargs)


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


def apply_backspaces_and_linefeeds(text):
    """
    Interpret backspaces and linefeeds in text like a terminal would.

    Interpret text like a terminal by removing backspace and linefeed
    characters and applying them line by line.

    If final line ends with a carriage it keeps it to be concatenable with next
    output chunk.
    """
    orig_lines = text.split('\n')
    orig_lines_len = len(orig_lines)
    new_lines = []
    for orig_line_idx, orig_line in enumerate(orig_lines):
        chars, cursor = [], 0
        orig_line_len = len(orig_line)
        for orig_char_idx, orig_char in enumerate(orig_line):
            if orig_char == '\r' and (orig_char_idx != orig_line_len - 1 or
                                      orig_line_idx != orig_lines_len - 1):
                cursor = 0
            elif orig_char == '\b':
                cursor = max(0, cursor - 1)
            else:
                if (orig_char == '\r' and
                        orig_char_idx == orig_line_len - 1 and
                        orig_line_idx == orig_lines_len - 1):
                    cursor = len(chars)
                if cursor == len(chars):
                    chars.append(orig_char)
                else:
                    chars[cursor] = orig_char
                cursor += 1
        new_lines.append(''.join(chars))
    return '\n'.join(new_lines)


def module_exists(modname):
    """Checks if a module exists without actually importing it."""
    return pkgutil.find_loader(modname) is not None


def modules_exist(*modnames):
    return all(module_exists(m) for m in modnames)


def module_is_in_cache(modname):
    """Checks if a module was imported before (is in the import cache)."""
    return modname in sys.modules


def module_is_imported(modname, scope=None):
    """Checks if a module is imported within the current namespace."""
    # return early if modname is not even cached
    if not module_is_in_cache(modname):
        return False

    if scope is None:  # use globals() of the caller by default
        scope = inspect.stack()[1][0].f_globals

    for m in scope.values():
        if isinstance(m, type(sys)) and m.__name__ == modname:
            return True

    return False


def ensure_wellformed_argv(argv):
    if argv is None:
        argv = sys.argv
    elif isinstance(argv, basestring):
        argv = shlex.split(argv)
    else:
        if not isinstance(argv, (list, tuple)):
            raise ValueError("argv must be str or list, but was {}"
                             .format(type(argv)))
        if not all([isinstance(a, basestring) for a in argv]):
            problems = [a for a in argv if not isinstance(a, basestring)]
            raise ValueError("argv must be list of str but contained the "
                             "following elements: {}".format(problems))
    return argv


class IntervalTimer(threading.Thread):
    @classmethod
    def create(cls, func, interval=10):
        stop_event = threading.Event()
        timer_thread = cls(stop_event, func, interval)
        return stop_event, timer_thread

    def __init__(self, event, func, interval=10.):
        threading.Thread.__init__(self)
        self.stopped = event
        self.func = func
        self.interval = interval

    def run(self):
        while not self.stopped.wait(self.interval):
            self.func()
        self.func()
