#!/usr/bin/env python
# coding=utf-8

import collections
import contextlib
import importlib
import logging
import pkgutil
import re
import shlex
import sys
import threading
import traceback as tb
from functools import partial
from packaging import version
from typing import Union
from pathlib import Path

import wrapt


__all__ = [
    "NO_LOGGER",
    "PYTHON_IDENTIFIER",
    "CircularDependencyError",
    "ObserverError",
    "SacredInterrupt",
    "TimeoutInterrupt",
    "create_basic_stream_logger",
    "recursive_update",
    "iterate_flattened",
    "iterate_flattened_separately",
    "set_by_dotted_path",
    "get_by_dotted_path",
    "iter_prefixes",
    "join_paths",
    "is_prefix",
    "convert_to_nested_dict",
    "convert_camel_case_to_snake_case",
    "print_filtered_stacktrace",
    "optional_kwargs_decorator",
    "get_inheritors",
    "apply_backspaces_and_linefeeds",
    "rel_path",
    "IntervalTimer",
    "PathType",
]

NO_LOGGER = logging.getLogger("ignore")
NO_LOGGER.disabled = 1

PATHCHANGE = object()

PYTHON_IDENTIFIER = re.compile("^[a-zA-Z_][_a-zA-Z0-9]*$")

PathType = Union[str, bytes, Path]


class ObserverError(Exception):
    """Error that an observer raises but that should not make the run fail."""


class SacredInterrupt(Exception):
    """Base-Class for all custom interrupts.

    For more information see :ref:`custom_interrupts`.
    """

    STATUS = "INTERRUPTED"


class TimeoutInterrupt(SacredInterrupt):
    """Signal that the experiment timed out.

    This exception can be used in client code to indicate that the run
    exceeded its time limit and has been interrupted because of that.
    The status of the interrupted run will then be set to ``TIMEOUT``.

    For more information see :ref:`custom_interrupts`.
    """

    STATUS = "TIMEOUT"


class SacredError(Exception):
    def __init__(
        self,
        message,
        print_traceback=True,
        filter_traceback="default",
        print_usage=False,
    ):
        super().__init__(message)
        self.print_traceback = print_traceback
        if filter_traceback not in ["always", "default", "never"]:
            raise ValueError(
                "filter_traceback must be one of 'always', "
                "'default' or 'never', not " + filter_traceback
            )
        self.filter_traceback = filter_traceback
        self.print_usage = print_usage


class CircularDependencyError(SacredError):
    """The ingredients of the current experiment form a circular dependency."""

    @classmethod
    @contextlib.contextmanager
    def track(cls, ingredient):
        try:
            yield
        except CircularDependencyError as e:
            if not e.__circular_dependency_handled__:
                if ingredient in e.__ingredients__:
                    e.__circular_dependency_handled__ = True
                e.__ingredients__.append(ingredient)
            raise e

    def __init__(
        self,
        message="Circular dependency detected:",
        ingredients=None,
        print_traceback=True,
        filter_traceback="default",
        print_usage=False,
    ):
        super().__init__(
            message,
            print_traceback=print_traceback,
            filter_traceback=filter_traceback,
            print_usage=print_usage,
        )

        if ingredients is None:
            ingredients = []
        self.__ingredients__ = ingredients
        self.__circular_dependency_handled__ = False

    def __str__(self):
        return super().__str__() + "->".join(
            [i.path for i in reversed(self.__ingredients__)]
        )


class ConfigError(SacredError):
    """Pretty prints the conflicting configuration values."""

    def __init__(
        self,
        message,
        conflicting_configs=(),
        print_conflicting_configs=True,
        print_traceback=True,
        filter_traceback="default",
        print_usage=False,
        config=None,
    ):
        super().__init__(
            message,
            print_traceback=print_traceback,
            filter_traceback=filter_traceback,
            print_usage=print_usage,
        )
        self.print_conflicting_configs = print_conflicting_configs

        if isinstance(conflicting_configs, str):
            conflicting_configs = (conflicting_configs,)

        self.__conflicting_configs__ = conflicting_configs
        self.__prefix_handled__ = False

        if config is None:
            config = {}
        self.__config__ = config

    @classmethod
    @contextlib.contextmanager
    def track(cls, config, prefix=None):
        try:
            yield
        except ConfigError as e:
            if not e.__prefix_handled__:
                if prefix:
                    e.__conflicting_configs__ = (
                        join_paths(prefix, str(c)) for c in e.__conflicting_configs__
                    )
                e.__config__ = config
                e.__prefix_handled__ = True
            raise e

    def __str__(self):
        s = super().__str__()
        if self.print_conflicting_configs:
            # Add a list formatted as below to the string s:
            #
            # Conflicting configuration values:
            #   a=3
            #   b.c=4
            s += "\nConflicting configuration values:"
            for conflicting_config in self.__conflicting_configs__:
                s += "\n  {}={}".format(
                    conflicting_config,
                    get_by_dotted_path(self.__config__, conflicting_config),
                )
        return s


class InvalidConfigError(ConfigError):
    """Can be raised in the user code if an error in the configuration is detected.

    Examples
    --------
    >>> # Experiment definitions ...
    ... @ex.automain
    ... def main(a, b):
    ...     if a != b['a']:
    ...         raise InvalidConfigError(
    ...                     'Need to be equal',
    ...                     conflicting_configs=('a', 'b.a'))
    """

    pass


class MissingConfigError(SacredError):
    """A config value that is needed by a captured function is not present in the provided config."""

    def __init__(
        self,
        message="Configuration values are missing:",
        missing_configs=(),
        print_traceback=False,
        filter_traceback="default",
        print_usage=True,
    ):
        message = "{} {}".format(message, missing_configs)
        super().__init__(
            message,
            print_traceback=print_traceback,
            filter_traceback=filter_traceback,
            print_usage=print_usage,
        )


class NamedConfigNotFoundError(SacredError):
    """A named config is not found."""

    def __init__(
        self,
        named_config,
        message="Named config not found:",
        available_named_configs=(),
        print_traceback=False,
        filter_traceback="default",
        print_usage=False,
    ):
        message = '{} "{}". Available config values are: {}'.format(
            message, named_config, available_named_configs
        )
        super().__init__(
            message,
            print_traceback=print_traceback,
            filter_traceback=filter_traceback,
            print_usage=print_usage,
        )


class ConfigAddedError(ConfigError):
    SPECIAL_ARGS = {"_log", "_config", "_seed", "__doc__", "config_filename", "_run"}
    """Special args that show up in the captured args but can never be set
    by the user"""

    def __init__(
        self,
        conflicting_configs,
        message="Added new config entry that is not used anywhere",
        captured_args=(),
        print_conflicting_configs=True,
        print_traceback=False,
        filter_traceback="default",
        print_usage=False,
        print_suggestions=True,
        config=None,
    ):
        super().__init__(
            message,
            conflicting_configs=conflicting_configs,
            print_conflicting_configs=print_conflicting_configs,
            print_traceback=print_traceback,
            filter_traceback=filter_traceback,
            print_usage=print_usage,
            config=config,
        )
        self.captured_args = captured_args
        self.print_suggestions = print_suggestions

    def __str__(self):
        s = super().__str__()
        if self.print_suggestions:
            possible_keys = set(self.captured_args) - self.SPECIAL_ARGS
            if possible_keys:
                s += "\nPossible config keys are: {}".format(possible_keys)
        return s


class SignatureError(SacredError, TypeError):
    """Error that is raised when the passed arguments do not match the functions signature."""

    def __init__(
        self,
        message,
        print_traceback=True,
        filter_traceback="always",
        print_usage=False,
    ):
        super().__init__(message, print_traceback, filter_traceback, print_usage)


class FilteredTracebackException(tb.TracebackException):
    """Filter out sacred internal tracebacks from an exception traceback."""

    def __init__(
        self,
        exc_type,
        exc_value,
        exc_traceback,
        *,
        limit=None,
        lookup_lines=True,
        capture_locals=False,
        _seen=None,
    ):
        exc_traceback = self._filter_tb(exc_traceback)
        self._walk_value(exc_value)
        super().__init__(
            exc_type,
            exc_value,
            exc_traceback,
            limit=limit,
            lookup_lines=lookup_lines,
            capture_locals=capture_locals,
            _seen=_seen,
        )

    def _walk_value(self, obj):
        if obj.__cause__:
            obj.__cause__.__traceback__ = self._filter_tb(obj.__cause__.__traceback__)
            self._walk_value(obj.__cause__)
        if obj.__context__:
            obj.__context__.__traceback__ = self._filter_tb(
                obj.__context__.__traceback__
            )
            self._walk_value(obj.__context__)

    def _filter_tb(self, tb):
        filtered_tb = []
        while tb is not None:
            if not _is_sacred_frame(tb.tb_frame):
                filtered_tb.append(tb)
            tb = tb.tb_next
        if len(filtered_tb) >= 2:
            for i in range(1, len(filtered_tb)):
                filtered_tb[i - 1].tb_next = filtered_tb[i]
        filtered_tb[-1].tb_next = None
        return filtered_tb[0]

    def format(self, *, chain=True):
        for line in super().format(chain=chain):
            if line == "Traceback (most recent call last):\n":
                yield "Traceback (most recent calls WITHOUT Sacred internals):\n"
            else:
                yield line


def create_basic_stream_logger():
    """Sets up a basic stream logger.

    Configures the root logger to use a
    `logging.StreamHandler` and sets the logging level to `logging.INFO`.

    Notes
    -----
        This does not change the logger configuration if the root logger
        already is configured (i.e. `len(getLogger().handlers) > 0`)
    """
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s"
    )
    return logging.getLogger("")


def recursive_update(d, u):
    """
    Given two dictionaries d and u, update dict d recursively.

    E.g.:
    d = {'a': {'b' : 1}}
    u = {'c': 2, 'a': {'d': 3}}
    => {'a': {'b': 1, 'd': 3}, 'c': 2}
    """
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
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
    manually_sorted_keys = manually_sorted_keys or []

    def get_order(key_and_value):
        key, value = key_and_value
        if key in manually_sorted_keys:
            return 0, manually_sorted_keys.index(key)
        elif not is_non_empty_dict(value):
            return 1, key
        else:
            return 2, key

    for key, value in sorted(dictionary.items(), key=get_order):
        if is_non_empty_dict(value):
            yield key, PATHCHANGE
            for k, val in iterate_flattened_separately(value, manually_sorted_keys):
                yield join_paths(key, k), val
        else:
            yield key, value


def is_non_empty_dict(python_object):
    return isinstance(python_object, dict) and python_object


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
    split_path = path.split(".")
    current_option = d
    for p in split_path[:-1]:
        if p not in current_option:
            current_option[p] = dict()
        current_option = current_option[p]
    current_option[split_path[-1]] = value


def get_by_dotted_path(d, path, default=None):
    """
    Get an entry from nested dictionaries using a dotted path.

    Example
    -------
    >>> get_by_dotted_path({'foo': {'a': 12}}, 'foo.a')
    12
    """
    if not path:
        return d
    split_path = path.split(".")
    current_option = d
    for p in split_path:
        if p not in current_option:
            return default
        current_option = current_option[p]
    return current_option


def iter_prefixes(path):
    """
    Iterate through all (non-empty) prefixes of a dotted path.

    Example
    -------
    >>> list(iter_prefixes('foo.bar.baz'))
    ['foo', 'foo.bar', 'foo.bar.baz']
    """
    split_path = path.split(".")
    for i in range(1, len(split_path) + 1):
        yield join_paths(*split_path[:i])


def join_paths(*parts):
    """Join different parts together to a valid dotted path."""
    return ".".join(str(p).strip(".") for p in parts if p)


def is_prefix(pre_path, path):
    """Return True if pre_path is a path-prefix of path."""
    pre_path = pre_path.strip(".")
    path = path.strip(".")
    return not pre_path or path.startswith(pre_path + ".")


def rel_path(base, path):
    """Return path relative to base."""
    if base == path:
        return ""
    assert is_prefix(base, path), "{} not a prefix of {}".format(base, path)
    return path[len(base) :].strip(".")


def convert_to_nested_dict(dotted_dict):
    """Convert a dict with dotted path keys to corresponding nested dict."""
    nested_dict = {}
    for k, v in iterate_flattened(dotted_dict):
        set_by_dotted_path(nested_dict, k, v)
    return nested_dict


def _is_sacred_frame(frame):
    return frame.f_globals["__name__"].split(".")[0] == "sacred"


def print_filtered_stacktrace(filter_traceback="default"):
    print(format_filtered_stacktrace(filter_traceback), file=sys.stderr)


def format_filtered_stacktrace(filter_traceback="default"):
    """
    Returns the traceback as `string`.

    `filter_traceback` can be one of:
        - 'always': always filter out sacred internals
        - 'default': Default behaviour: filter out sacred internals
                if the exception did not originate from within sacred, and
                print just the internal stack trace otherwise
        - 'never': don't filter, always print full traceback
        - All other values will fall back to 'never'.
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()
    # determine if last exception is from sacred
    current_tb = exc_traceback
    while current_tb.tb_next is not None:
        current_tb = current_tb.tb_next

    if filter_traceback == "default" and _is_sacred_frame(current_tb.tb_frame):
        # just print sacred internal trace
        header = [
            "Exception originated from within Sacred.\n"
            "Traceback (most recent calls):\n"
        ]
        texts = tb.format_exception(exc_type, exc_value, current_tb)
        return "".join(header + texts[1:]).strip()
    elif filter_traceback in ("default", "always"):
        # print filtered stacktrace
        tb_exception = FilteredTracebackException(
            exc_type, exc_value, exc_traceback, limit=None
        )
        return "".join(tb_exception.format())
    elif filter_traceback == "never":
        # print full stacktrace
        return "\n".join(tb.format_exception(exc_type, exc_value, exc_traceback))
    else:
        raise ValueError("Unknown value for filter_traceback: " + filter_traceback)


def format_sacred_error(e, short_usage):
    lines = []
    if e.print_usage:
        lines.append(short_usage)
    if e.print_traceback:
        lines.append(format_filtered_stacktrace(e.filter_traceback))
    else:
        lines.append("\n".join(tb.format_exception_only(type(e), e)))
    return "\n".join(lines)


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
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def apply_backspaces_and_linefeeds(text):
    """
    Interpret backspaces and linefeeds in text like a terminal would.

    Interpret text like a terminal by removing backspace and linefeed
    characters and applying them line by line.

    If final line ends with a carriage it keeps it to be concatenable with next
    output chunk.
    """
    orig_lines = text.split("\n")
    orig_lines_len = len(orig_lines)
    new_lines = []
    for orig_line_idx, orig_line in enumerate(orig_lines):
        chars, cursor = [], 0
        orig_line_len = len(orig_line)
        for orig_char_idx, orig_char in enumerate(orig_line):
            if orig_char == "\r" and (
                orig_char_idx != orig_line_len - 1
                or orig_line_idx != orig_lines_len - 1
            ):
                cursor = 0
            elif orig_char == "\b":
                cursor = max(0, cursor - 1)
            else:
                if (
                    orig_char == "\r"
                    and orig_char_idx == orig_line_len - 1
                    and orig_line_idx == orig_lines_len - 1
                ):
                    cursor = len(chars)
                if cursor == len(chars):
                    chars.append(orig_char)
                else:
                    chars[cursor] = orig_char
                cursor += 1
        new_lines.append("".join(chars))
    return "\n".join(new_lines)


def module_exists(modname):
    """Checks if a module exists without actually importing it."""
    try:
        return pkgutil.find_loader(modname) is not None
    except ImportError:
        # TODO: Temporary fix for tf 1.14.0.
        # Should be removed once fixed in tf.
        return True


def modules_exist(*modnames):
    return all(module_exists(m) for m in modnames)


def module_is_in_cache(modname):
    """Checks if a module was imported before (is in the import cache)."""
    return modname in sys.modules


def parse_version(version_string):
    """Returns a parsed version string."""
    return version.parse(version_string)


def get_package_version(name):
    """Returns a parsed version string of a package."""
    version_string = importlib.import_module(name).__version__
    return parse_version(version_string)


def ensure_wellformed_argv(argv):
    if argv is None:
        argv = sys.argv
    elif isinstance(argv, str):
        argv = shlex.split(argv)
    else:
        if not isinstance(argv, (list, tuple)):
            raise ValueError("argv must be str or list, but was {}".format(type(argv)))
        if not all([isinstance(a, str) for a in argv]):
            problems = [a for a in argv if not isinstance(a, str)]
            raise ValueError(
                "argv must be list of str but contained the "
                "following elements: {}".format(problems)
            )
    return argv


class IntervalTimer(threading.Thread):
    @classmethod
    def create(cls, func, interval=10):
        stop_event = threading.Event()
        timer_thread = cls(stop_event, func, interval)
        return stop_event, timer_thread

    def __init__(self, event, func, interval=10.0):
        super().__init__()
        self.stopped = event
        self.func = func
        self.interval = interval

    def run(self):
        while not self.stopped.wait(self.interval):
            self.func()
        self.func()
