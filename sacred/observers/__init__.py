#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from sacred.observers.base import RunObserver
import sacred.optional as opt

if opt.has_pymongo:
    from sacred.observers.mongo import MongoObserver
else:
    MongoObserver = opt.MissingDependencyMock('pymongo')

__all__ = ('RunObserver', 'MongoObserver')
