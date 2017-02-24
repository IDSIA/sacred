#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from sacred.commandline_options import CommandLineOption

from sacred.observers.base import RunObserver
from sacred.observers.file_storage import FileStorageObserver
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

if opt.has_sqlalchemy:
    from sacred.observers.sql import SqlObserver
else:
    SqlObserver = opt.MissingDependencyMock('sqlalchemy')

    class SqlOption(CommandLineOption):
        """To use the SqlObserver you need to install sqlalchemy first."""

        arg = 'DB_URL'

        @classmethod
        def apply(cls, args, run):
            raise ImportError('cannot use -s/--sql flag: '
                              'missing sqlalchemy dependency')


if opt.has_tinydb:
    from sacred.observers.tinydb_hashfs import TinyDbObserver, TinyDbReader
else:
    TinyDbObserver = opt.MissingDependencyMock(
        ['tinydb', 'tinydb-serialization', 'hashfs'])
    TinyDbReader = opt.MissingDependencyMock(
        ['tinydb', 'tinydb-serialization', 'hashfs'])

    class TinyDbOption(CommandLineOption):
        """To use the TinyDBObserver you need to install tinydb first."""

        arg = 'BASEDIR'

        @classmethod
        def apply(cls, args, run):
            raise ImportError('cannot use -t/--tiny_db flag: '
                              'missing tinydb dependency')


if opt.has_requests:
    from sacred.observers.slack import SlackObserver
else:
    SlackObserver = opt.MissingDependencyMock('requests')

if opt.has_telegram:
    from sacred.observers.telegram import TelegramObserver
else:
    TelegramObserver = opt.MissingDependencyMock('telegram')


__all__ = ('FileStorageObserver', 'RunObserver', 'MongoObserver',
           'SqlObserver', 'TinyDbObserver', 'TinyDbReader',
           'SlackObserver', 'TelegramObserver')
