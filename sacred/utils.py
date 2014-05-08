#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
import logging
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

        self.ex._emit_info_updated()


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


##### Portable way of raising exceptions with traceback #######

if sys.version_info[0] == 2:
    PYTHON2_RAISE = """
def raise_with_traceback(exc, traceback):
    raise exc, None, traceback
"""
    exec PYTHON2_RAISE
else:
    def raise_with_traceback(exc, traceback):
        raise exc.with_traceback(traceback)
