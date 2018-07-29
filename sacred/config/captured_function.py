#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import time
from datetime import timedelta

import wrapt
from sacred.config.custom_containers import FallbackDict
from sacred.config.signature import Signature
from sacred.randomness import create_rnd, get_seed
from sacred.utils import ConfigError, MissingConfigError


def create_captured_function(function, prefix=None, ingredient=None):
    sig = Signature(function)
    function.signature = sig
    function.uses_randomness = ("_seed" in sig.arguments or
                                "_rnd" in sig.arguments)
    function.logger = None
    function.config = {}
    function.rnd = None
    function.run = None
    function.prefix = prefix
    function.ingredient = ingredient
    return captured_function(function)


@wrapt.decorator
def captured_function(wrapped, instance, args, kwargs):
    options = FallbackDict(
        wrapped.config,
        _config=wrapped.config,
        _log=wrapped.logger,
        _run=wrapped.run
    )
    if wrapped.uses_randomness:  # only generate _seed and _rnd if needed
        options['_seed'] = get_seed(wrapped.rnd)
        options['_rnd'] = create_rnd(options['_seed'])

    bound = (instance is not None)
    try:
        args, kwargs = wrapped.signature.construct_arguments(args, kwargs,
                                                             options,
                                                             bound)
    except MissingConfigError as e:
        if e.func is None:
            e.func = wrapped
        raise e

    if wrapped.logger is not None:
        wrapped.logger.debug("Started")
        start_time = time.time()
    # =================== run actual function =================================
    try:
        result = wrapped(*args, **kwargs)
    except ConfigError as e:
        if not e.__prefix_handled__:
            if wrapped.prefix:
                e.conflicting_configs = ('.'.join((wrapped.prefix, str(c))) for
                                         c in e.conflicting_configs)
            e.__config_sources__ = wrapped.sources
            e.__config__ = wrapped.config
        e.__prefix_handled__ = True
        raise e
    # =========================================================================
    if wrapped.logger is not None:
        stop_time = time.time()
        elapsed_time = timedelta(seconds=round(stop_time - start_time))
        wrapped.logger.debug("Finished after %s.", elapsed_time)

    return result
