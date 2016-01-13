#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from sacred.commandline_options import CommandLineOption

from sacred.observers.base import RunObserver
import sacred.optional as opt

if opt.has_pymongo:
    from sacred.observers.mongo import MongoObserver
else:
    MongoObserver = opt.MissingDependencyMock('pymongo')

    class MongoDbOption(CommandLineOption):
        """To use the MongoObserver you need to install pymongo first."""

        arg = 'DB'

        @classmethod
        def apply(cls, args, run):
            raise ImportError('cannot use -m/--mongo_db flag: '
                              'missing pymongo dependency')


__all__ = ('RunObserver', 'MongoObserver')
