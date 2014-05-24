#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from datetime import timedelta
import time
from sacred.signature import Signature
import wrapt
from utils import get_seed, create_rnd


class FallbackDict(dict):
    """
    This dictionary either returns the value assigned to a given key or it
    returns the value for that key from the fallback dict.
    """
    def __init__(self, fallback, **kwargs):
        super(FallbackDict, self).__init__(**kwargs)
        self.fallback = fallback

    def __getitem__(self, item):
        if dict.__contains__(self, item):
            return dict.__getitem__(self, item)
        else:
            return self.fallback[item]

    def __contains__(self, item):
        return dict.__contains__(self, item) or (item in self.fallback)

    def get(self, k, d=None):
        if dict.__contains__(self, k):
            return dict.__getitem__(self, k)()
        else:
            return self.fallback.get(k, d)

    def has_key(self, item):
        return self.__contains__(item)

    def items(self):
        raise NotImplemented

    def iteritems(self):
        raise NotImplemented

    def iterkeys(self):
        raise NotImplemented

    def itervalues(self):
        raise NotImplemented

    def keys(self):
        raise NotImplemented

    def pop(self, k, d=None):
        raise NotImplemented

    def popitem(self):
        raise NotImplemented

    def setdefault(self, k, d=None):
        raise NotImplemented

    def update(self, E=None, **F):
        raise NotImplemented

    def values(self):
        raise NotImplemented

    def viewitems(self):
        raise NotImplemented

    def viewkeys(self):
        raise NotImplemented

    def viewvalues(self):
        raise NotImplemented

    def __iter__(self):
        raise NotImplemented

    def __len__(self):
        raise NotImplemented


def create_captured_function(f):
    f.signature = Signature(f)
    f.logger = None
    f.config = {}
    f.seed = None
    f.rnd = None
    return captured_function(f)


@wrapt.decorator
def captured_function(wrapped, instance, args, kwargs):
    runseed = get_seed(wrapped.rnd)
    options = FallbackDict(
        wrapped.config,
        log=wrapped.logger,
        seed=runseed,
        rnd=create_rnd(runseed)
    )
    args, kwargs = wrapped.signature.construct_arguments(args, kwargs, options)
    wrapped.logger.info("started")
    start_time = time.time()
    ####################### run actual function ############################
    result = wrapped(*args, **kwargs)
    ########################################################################
    stop_time = time.time()
    elapsed_time = timedelta(seconds=round(stop_time - start_time))
    wrapped.logger.info("finished after %s." % elapsed_time)

    return result
