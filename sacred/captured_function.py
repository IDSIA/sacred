#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from datetime import timedelta
import time

import wrapt

from sacred.custom_containers import FallbackDict
from sacred.signature import Signature
from sacred.utils import create_rnd, get_seed

__sacred__ = True


def create_captured_function(f, prefix=None):
    f.signature = Signature(f)
    f.logger = None
    f.config = {}
    f.rnd = None
    f.run = None
    f.prefix = prefix
    return captured_function(f)


@wrapt.decorator
def captured_function(wrapped, instance, args, kwargs):
    # todo: performance optimize this by only creating a PRNG if the signature
    # contains either _seed or _rnd
    runseed = get_seed(wrapped.rnd)
    options = FallbackDict(
        wrapped.config,
        _log=wrapped.logger,
        _seed=runseed,
        _rnd=create_rnd(runseed),
        _run=wrapped.run
    )
    args, kwargs = wrapped.signature.construct_arguments(args, kwargs, options)
    wrapped.logger.debug("Started")
    start_time = time.time()
    ####################### run actual function ############################
    result = wrapped(*args, **kwargs)
    ########################################################################
    stop_time = time.time()
    elapsed_time = timedelta(seconds=round(stop_time - start_time))
    wrapped.logger.debug("Finished after %s." % elapsed_time)

    return result
