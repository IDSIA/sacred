#!/usr/bin/python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from .signature import Signature


class CapturedFunction(object):
    def __init__(self, f, parent):
        self._wrapped_function = f
        self.__doc__ = f.__doc__
        self.__name__ = f.__name__
        self._parent_experiment = parent
        self._signature = Signature(f)

    def execute(self, args, kwargs, options):
        args, kwargs = self._signature.construct_arguments(args, kwargs, options)
        result = self._wrapped_function(*args, **kwargs)
        return result

    def __call__(self, *args, **kwargs):
        return self.execute(args, kwargs, self._parent_experiment.config)