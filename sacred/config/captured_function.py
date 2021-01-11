#!/usr/bin/env python
# coding=utf-8

import time
from datetime import timedelta

import wrapt
from sacred.config.custom_containers import fallback_dict
from sacred.config.signature import Signature
from sacred.randomness import create_rnd, get_seed
from sacred.utils import ConfigError


def create_captured_function(function, prefix=None):
    sig = Signature(function)
    function.signature = sig
    function.uses_randomness = "_seed" in sig.arguments or "_rnd" in sig.arguments
    function.logger = None
    function.config = {}
    function.rnd = None
    function.run = None
    function.prefix = prefix
    return captured_function(function)


@wrapt.decorator
def captured_function(wrapped, instance, args, kwargs):
    options = fallback_dict(
        wrapped.config, _config=wrapped.config, _log=wrapped.logger, _run=wrapped.run
    )
    if wrapped.uses_randomness:  # only generate _seed and _rnd if needed
        options["_seed"] = get_seed(wrapped.rnd)
        options["_rnd"] = create_rnd(options["_seed"])

    bound = instance is not None
    args, kwargs = wrapped.signature.construct_arguments(args, kwargs, options, bound)
    if wrapped.logger is not None:
        wrapped.logger.debug("Started")
        start_time = time.time()
    # =================== run actual function =================================
    with ConfigError.track(wrapped.config, wrapped.prefix):
        result = wrapped(*args, **kwargs)
    # =========================================================================
    if wrapped.logger is not None:
        stop_time = time.time()
        elapsed_time = timedelta(seconds=round(stop_time - start_time))
        wrapped.logger.debug("Finished after %s.", elapsed_time)

    return result
