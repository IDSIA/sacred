#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import pytest

pymongo = pytest.importorskip("pymongo")

from sacred.observers.mongo import MongoDbOption, DEFAULT_MONGO_PRIORITY


def test_parse_mongo_db_arg():
    assert MongoDbOption.parse_mongo_db_arg('foo') == (
        'localhost:27017', 'foo', '', DEFAULT_MONGO_PRIORITY)


def test_parse_mongo_db_arg_collection():
    assert MongoDbOption.parse_mongo_db_arg('foo.bar') == (
        'localhost:27017', 'foo', 'bar', DEFAULT_MONGO_PRIORITY)


def test_parse_mongo_db_arg_hostname():
    assert MongoDbOption.parse_mongo_db_arg('localhost:28017') == \
        ('localhost:28017', 'sacred', '', DEFAULT_MONGO_PRIORITY)

    assert MongoDbOption.parse_mongo_db_arg('www.mymongo.db:28017') == \
        ('www.mymongo.db:28017', 'sacred', '', DEFAULT_MONGO_PRIORITY)

    assert MongoDbOption.parse_mongo_db_arg('123.45.67.89:27017') == \
        ('123.45.67.89:27017', 'sacred', '', DEFAULT_MONGO_PRIORITY)


def test_parse_mongo_db_arg_hostname_dbname():
    assert MongoDbOption.parse_mongo_db_arg('localhost:28017:foo') == \
        ('localhost:28017', 'foo', '', DEFAULT_MONGO_PRIORITY)

    assert MongoDbOption.parse_mongo_db_arg('www.mymongo.db:28017:bar') == \
        ('www.mymongo.db:28017', 'bar', '', DEFAULT_MONGO_PRIORITY)

    assert MongoDbOption.parse_mongo_db_arg('123.45.67.89:27017:baz') == \
        ('123.45.67.89:27017', 'baz', '', DEFAULT_MONGO_PRIORITY)


def test_parse_mongo_db_arg_hostname_dbname_collection_name():
    assert MongoDbOption.parse_mongo_db_arg('localhost:28017:foo.bar') == \
        ('localhost:28017', 'foo', 'bar', DEFAULT_MONGO_PRIORITY)

    assert MongoDbOption.parse_mongo_db_arg('www.mymongo.db:28017:bar.baz') ==\
        ('www.mymongo.db:28017', 'bar', 'baz', DEFAULT_MONGO_PRIORITY)

    assert MongoDbOption.parse_mongo_db_arg('123.45.67.89:27017:baz.foo') == \
        ('123.45.67.89:27017', 'baz', 'foo', DEFAULT_MONGO_PRIORITY)


def test_parse_mongo_db_arg_priority():
    assert MongoDbOption.parse_mongo_db_arg('localhost:28017:foo.bar!17') == \
        ('localhost:28017', 'foo', 'bar', 17)

    assert MongoDbOption.parse_mongo_db_arg('www.mymongo.db:28017:bar.baz!2') ==\
        ('www.mymongo.db:28017', 'bar', 'baz', 2)

    assert MongoDbOption.parse_mongo_db_arg('123.45.67.89:27017:baz.foo!-123') == \
        ('123.45.67.89:27017', 'baz', 'foo', -123)
