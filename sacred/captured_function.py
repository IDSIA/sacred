#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from datetime import timedelta
import time
from sacred.signature import Signature


class CapturedFunction(object):
    def __init__(self, f):
        self._wrapped_function = f
        self.__doc__ = f.__doc__
        self.__name__ = f.__name__
        self.config = {}
        self._signature = Signature(f)
        self.logger = None

    def execute(self, args, kwargs, options=None):
        opt = dict(options) if options is not None else dict()
        if 'log' in self._signature.arguments:
            opt['log'] = self.logger
        args, kwargs = self._signature.construct_arguments(args, kwargs, opt)
        self.logger.info("started")
        start_time = time.time()
        ####################### run actual function ############################
        result = self._wrapped_function(*args, **kwargs)
        ########################################################################
        stop_time = time.time()
        elapsed_time = timedelta(seconds=round(stop_time - start_time))
        self.logger.info("finished after %s." % elapsed_time)
        return result

    def __call__(self, *args, **kwargs):
        return self.execute(args, kwargs, self.config)