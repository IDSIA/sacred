#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
import collections
from contextlib import contextmanager
import logging
from StringIO import StringIO
import sys
import random

NO_LOGGER = logging.getLogger('ignore')
NO_LOGGER.disabled = 1
SEEDRANGE = (1, 1e9)

# TODO: Remove this and put into separate package (maybe a plugin?)
try:
    from pylstm.training.monitoring import Monitor

    class InfoUpdater(Monitor):
        def __init__(self, experiment, name=None):
            super(InfoUpdater, self).__init__(name, 'epoch', 1)
            self.ex = experiment
            self.__name__ = self.__class__.__name__ if name is None else name

        def __call__(self, epoch, net, stepper, logs):
            info = self.ex.info
            info['epochs_needed'] = epoch
            info['monitor'] = logs
            if 'nr_parameters' not in info:
                info['nr_parameters'] = net.get_param_size()
except ImportError:
    pass


def create_basic_stream_logger(name, level=None):
    level = level if level is not None else logging.INFO
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers = []
    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def recursive_update(d, u):
    """
    Given two dictionaries d and u, update dict d recursively.

    E.g.:
    d = {'a': {'b' : 1}}
    u = {'c': 2, 'a' : {'d': 3}}
    => {'a': {'b': 1, 'd': 3}, 'c': 2}
    """
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = recursive_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


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
        return random.randint(*SEEDRANGE)
    return rnd.randint(*SEEDRANGE)


def create_rnd(seed):
    return random.Random(seed)


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


def iterate_flattened(d):
    """
    Iterate over a dictionary recursively, providing full dotted
    paths for every item.
    """
    if isinstance(d, dict):
        for key, value in d.items():
            yield key, value
            for k, v in iterate_flattened(d[key]):
                yield key + '.' + k, v


def set_by_dotted_path(d, path, value):
    split_path = path.split('.')
    current_option = d
    for p in split_path[:-1]:
        if p not in current_option:
            current_option[p] = dict()
        current_option = current_option[p]
    assert split_path[-1], "empty path or trailing dot ('%s')" % path
    current_option[split_path[-1]] = value


def get_by_dotted_path(d, path):
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
    split_path = path.split('.')
    for i in range(len(split_path)):
        p1 = '.'.join(split_path[:i])
        p2 = '.'.join(split_path[i:])
        yield p1, p2


def join_paths(*parts):
    return '.'.join(parts).strip('.')