#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import time
from datetime import timedelta

import wrapt
from sacred.config.custom_containers import FallbackDict
from sacred.config.signature import Signature
from sacred.randomness import create_rnd, get_seed

__sacred__ = True


def create_captured_function(function, prefix=None):
    sig = Signature(function)
    function.signature = sig
    function.uses_randomness = ("_seed" in sig.arguments or
                                "_rnd" in sig.arguments)
    function.logger = None
    function.config = {}
    function.rnd = None
    function.run = None
    function.prefix = prefix
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
    args, kwargs = wrapped.signature.construct_arguments(args, kwargs, options,
                                                         bound)
    wrapped.logger.debug("Started")
    start_time = time.time()
    # =================== run actual function =================================
    result = wrapped(*args, **kwargs)
    # =========================================================================
    stop_time = time.time()
    elapsed_time = timedelta(seconds=round(stop_time - start_time))
    wrapped.logger.debug("Finished after %s.", elapsed_time)

    return result
