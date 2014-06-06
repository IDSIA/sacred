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
