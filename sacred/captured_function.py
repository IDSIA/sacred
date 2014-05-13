#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from datetime import timedelta
import sys
import time
from sacred.signature import Signature
from sacred.utils import raise_with_traceback


class CapturedFunction(object):
    def __init__(self, f, parent):
        self._wrapped_function = f
        self.__doc__ = f.__doc__
        self.__name__ = f.__name__
        self._parent_experiment = parent
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
        try:
            result = self._wrapped_function(*args, **kwargs)
        except:
            t, v, trace = sys.exc_info()
            raise_with_traceback(v, trace.tb_next)
            raise  # to make IDE happy
        ########################################################################
        stop_time = time.time()
        elapsed_time = timedelta(seconds=round(stop_time - start_time))
        self.logger.info("finished after %s." % elapsed_time)
        return result

    def __call__(self, *args, **kwargs):
        try:
            return self.execute(args, kwargs, self._parent_experiment.cfg)
        except:
            t, v, trace = sys.exc_info()
            raise_with_traceback(v, trace.tb_next)
            raise  # to make IDE happy