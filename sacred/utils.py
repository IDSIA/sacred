#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
import collections
from contextlib import contextmanager
import logging
import sys
import traceback as tb

try:
    from numpy.random import randint
    from numpy.random import RandomState as Random
except ImportError:
    from random import randint
    from random import Random

__sacred__ = True  # marker for filtering stacktraces when run from commandline


if sys.version_info[0] == 3:
    import io
    StringIO = io.StringIO
else:
    from StringIO import StringIO

NO_LOGGER = logging.getLogger('ignore')
NO_LOGGER.disabled = 1
SEEDRANGE = (1, 1e9)


def create_basic_stream_logger(name, level=None):
    level = level if level is not None else logging.INFO
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers = []
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def recursive_update(dictionary, updates):
    """
    Given two dictionaries, update dictionary based on updates recursively.

    E.g.:
    d = {'a': {'b' : 1}}
    u = {'c': 2, 'a': {'d': 3}}
    => {'a': {'b': 1, 'd': 3}, 'c': 2}
    """
    for key, value in updates.items():
        if isinstance(value, collections.Mapping):
            updated = recursive_update(dictionary.get(key, {}), value)
            dictionary[key] = updated
        else:
            dictionary[key] = updates[key]
    return dictionary


class Tee(object):
    def __init__(self, out1, out2):
        self.out1 = out1
        self.out2 = out2

    def write(self, data):
        self.out1.write(data)
        self.out2.write(data)

    def flush(self):
        self.out1.flush()
        self.out2.flush()


@contextmanager
def tee_output():
    out = StringIO()
    sys.stdout = Tee(sys.stdout, out)
    sys.stderr = Tee(sys.stderr, out)
    yield out
    sys.stdout = sys.stdout.out1
    sys.stderr = sys.stderr.out1
    out.close()


def get_seed(rnd=None):
    if rnd is None:
        return randint(*SEEDRANGE)
    return rnd.randint(*SEEDRANGE)


def create_rnd(seed):
    return Random(seed)


def iterate_separately(dictionary):
    """
    Iterate over the items of a dictionary. First iterate over all items that
    are non-dictionary values (sorted by keys), then over the rest
    (sorted by keys).
    """
    single_line_keys = [k for k in dictionary.keys()
                        if not isinstance(dictionary[k], dict)]
    for k in sorted(single_line_keys):
        yield k, dictionary[k]

    multi_line_keys = [k for k in dictionary.keys()
                       if isinstance(dictionary[k], dict)]
    for k in sorted(multi_line_keys):
        yield k, dictionary[k]


def iterate_flattened(dictionary):
    """
    Iterate over a dictionary recursively, providing full dotted
    paths for every leaf.
    """
    for key in sorted(dictionary.keys()):
        value = dictionary[key]
        if isinstance(value, dict):
            for sub_key, sub_value in iterate_flattened(value):
                yield join_paths(key, sub_key), sub_value
        else:
            yield key, value


def set_by_dotted_path(dictionary, path, value):
    """
    Set an entry in a nested dict using a dotted path. Will create dictionaries
    as needed.

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
    current_option = dictionary
    for part in split_path[:-1]:
        if part not in current_option:
            current_option[part] = dict()
        current_option = current_option[part]
    current_option[split_path[-1]] = value


def get_by_dotted_path(dictionary, path):
    """
    Get an entry from nested dictionaries using a dotted path.

    Example:
    >>> get_by_dotted_path({'foo': {'a': 12}}, 'foo.a')
    12
    """
    if not path:
        return dictionary
    split_path = path.split('.')
    current_option = dictionary
    for part in split_path:
        if part not in current_option:
            return None
        current_option = current_option[part]
    return current_option


def iter_path_splits(path):
    """
    Iterate over possible splits of a dotted path. The first part can be empty
    the second should not be.

    Example:
    >>> list(iter_path_splits('foo.bar.baz'))
    [('',        'foo.bar.baz'),
     ('foo',     'bar.baz'),
     ('foo.bar', 'baz')]
    """
    split_path = path.split('.')
    for i in range(len(split_path)):
        path1 = join_paths(*split_path[:i])
        path2 = join_paths(*split_path[i:])
        yield path1, path2


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
    """
    Join different parts together to a valid dotted path.
    """
    return '.'.join(p.strip('.') for p in parts if p)


def is_prefix(pre_path, path):
    """
    Returns True if pre_path is a path-prefix of path.
    """
    pre_path = pre_path.strip('.')
    path = path.strip('.')
    return not pre_path or path.startswith(pre_path + '.')


def convert_to_nested_dict(dotted_dict):
    """
    Convert a dictionary where some of the keys might be dotted paths to the
    corresponding nested dictionary.
    """
    nested_dict = {}
    for key, value in iterate_flattened(dotted_dict):
        set_by_dotted_path(nested_dict, key, value)
    return nested_dict


def print_filtered_stacktrace():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    print("Traceback (most recent calls WITHOUT sacred internals):",
          file=sys.stderr)
    current_tb = exc_traceback
    while current_tb is not None:
        if '__sacred__' not in current_tb.tb_frame.f_globals:
            tb.print_tb(current_tb, 1)
        current_tb = current_tb.tb_next
    tb.print_exception(exc_type, exc_value, None)
