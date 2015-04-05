#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals


class MissingDependencyMock(object):
    def __init__(self, depends_on):
        self.depends_on = depends_on

    def __getattribute__(self, item):
        if item.startswith('__'):
            return object.__getattribute__(self, item)
        raise ImportError('Depends on missing "{}" package.'
                          .format(object.__getattribute__(self, 'depends_on')))

    def __call__(self, *args, **kwargs):
        raise ImportError('Depends on missing "{}" package.'
                          .format(object.__getattribute__(self, 'depends_on')))


try:
    import numpy as np
    has_numpy = True
except ImportError:
    np = None
    has_numpy = False


try:
    import pymongo
    import bson
    import gridfs
    has_pymongo = True
except ImportError:
    pymongo = bson = gridfs = None
    has_pymongo = False


try:
    import yaml
    has_yaml = True
except ImportError:
    yaml = None
    has_yaml = False
