#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from datetime import timedelta
import time
from sacred.signature import Signature
import wrapt


def create_captured_function(f):
    f.signature = Signature(f)
    f.logger = None
    f.config = {}
    return captured_function(f)


@wrapt.decorator
def captured_function(wrapped, instance, args, kwargs):
    # if 'log' in wrapped._signature.arguments:
    #     opt['log'] = wrapped.logger
    args, kwargs = wrapped.signature.construct_arguments(args, kwargs,
                                                         wrapped.config)
    wrapped.logger.info("started")
    start_time = time.time()
    ####################### run actual function ############################
    result = wrapped(*args, **kwargs)
    ########################################################################
    stop_time = time.time()
    elapsed_time = timedelta(seconds=round(stop_time - start_time))
    wrapped.logger.info("finished after %s." % elapsed_time)

    return result
