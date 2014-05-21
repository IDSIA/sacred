#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
import collections
from contextlib import contextmanager
import logging
from StringIO import StringIO
import sys


class InfoUpdater(object):
    def __init__(self, experiment, monitors=None, name=None):
        self.ex = experiment
        self.__name__ = self.__class__.__name__ if name is None else name
        self.monitors = dict()
        if isinstance(monitors, dict):
            self.monitors = monitors
        elif isinstance(monitors, (list, set)):
            self.monitors = {str(i): m for i, m in enumerate(monitors)}
        else:
            self.monitors[''] = monitors

    def __call__(self, epoch, net, training_errors, validation_errors, **_):
        info = self.ex.description['info']

        info['epochs_needed'] = epoch
        info['training_errors'] = training_errors
        info['validation_errors'] = validation_errors
        if 'nr_parameters' not in info:
            info['nr_parameters'] = net.get_param_size()

        if self.monitors and 'monitor' not in info:
            monitors = {}
            for mon_name, mon in self.monitors.items():
                if not hasattr(mon, 'log') or len(mon.log) == 0:
                    continue

                if len(mon.log) == 1:
                    log_name = mon.log.keys()[0]
                    monitors[mon_name + '/' + log_name] = mon.log[log_name]
                else:
                    monitors[mon_name] = mon.log

            info['monitor'] = monitors


def create_basic_stream_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers = []
    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

NO_LOGGER = logging.getLogger('ignore')
NO_LOGGER.disabled = 1


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



