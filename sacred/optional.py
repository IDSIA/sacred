#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import importlib


class MissingDependencyMock(object):
    def __init__(self, depends_on):
        self.depends_on = depends_on

    def __getattribute__(self, item):
        raise ImportError('Depends on missing "{}" package.'
                          .format(object.__getattribute__(self, 'depends_on')))

    def __call__(self, *args, **kwargs):
        raise ImportError('Depends on missing "{}" package.'
                          .format(object.__getattribute__(self, 'depends_on')))


def optional_import(package_name):
    try:
        p = importlib.import_module(package_name)
        return True, p
    except ImportError:
        return False, None

has_pymongo, pymongo = optional_import('pymongo')
has_numpy, np = optional_import('numpy')
has_yaml, yaml = optional_import('yaml')
has_pandas, pandas = optional_import('pandas')
