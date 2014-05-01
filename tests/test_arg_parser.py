#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals

from sacred.arg_parser import parse_mongo_db_arg


def test_parse_mongo_db_arg():
    assert parse_mongo_db_arg('foo') == ('localhost:27017', 'foo')


def test_parse_mongo_db_arg_hostname():
    assert parse_mongo_db_arg('localhost:28017') == ('localhost:28017', 'sperment')

    assert parse_mongo_db_arg('www.mymongo.db:28017') == ('www.mymongo.db:28017', 'sperment')

    assert parse_mongo_db_arg('123.45.67.89:27017') == ('123.45.67.89:27017', 'sperment')


def test_parse_mongo_db_arg_hostname_dbname():
    assert parse_mongo_db_arg('localhost:28017:foo') == ('localhost:28017', 'foo')

    assert parse_mongo_db_arg('www.mymongo.db:28017:bar') == ('www.mymongo.db:28017', 'bar')

    assert parse_mongo_db_arg('123.45.67.89:27017:baz') == ('123.45.67.89:27017', 'baz')