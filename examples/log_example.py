#!/usr/bin/env python
# coding=utf-8
""" An example showcasing the logging system of Sacred."""
from __future__ import division, print_function, unicode_literals
import logging
from sacred import Experiment

ex = Experiment('log_example')

# set up a custom logger
logger = logging.getLogger('mylogger')
logger.handlers = []
ch = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname).1s] %(name)s >> "%(message)s"')
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.setLevel('INFO')

# attach it to the experiment
ex.logger = logger


@ex.config
def cfg():
    number = 2
    got_gizmo = False


@ex.capture
def transmogrify(got_gizmo, number, _log):
    if got_gizmo:
        _log.debug("Got gizmo. Performing transmogrification...")
        return number * 42
    else:
        _log.warning("No gizmo. Can't transmogrify!")
        return 0


@ex.automain
def main(number, _log):
    _log.info('Attempting to transmogrify %d...', number)
    result = transmogrify()
    _log.info('Transmogrification complete: %d', result)
    return result
