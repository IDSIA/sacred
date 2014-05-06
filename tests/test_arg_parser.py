#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
import pytest
from sacred.arg_parser import parse_mongo_db_arg, parse_arguments


def test_parse_mongo_db_arg():
    assert parse_mongo_db_arg('foo') == ('localhost:27017', 'foo')


def test_parse_mongo_db_arg_hostname():
    assert parse_mongo_db_arg('localhost:28017') == ('localhost:28017', 'sacred')

    assert parse_mongo_db_arg('www.mymongo.db:28017') == ('www.mymongo.db:28017', 'sacred')

    assert parse_mongo_db_arg('123.45.67.89:27017') == ('123.45.67.89:27017', 'sacred')


def test_parse_mongo_db_arg_hostname_dbname():
    assert parse_mongo_db_arg('localhost:28017:foo') == ('localhost:28017', 'foo')

    assert parse_mongo_db_arg('www.mymongo.db:28017:bar') == ('www.mymongo.db:28017', 'bar')

    assert parse_mongo_db_arg('123.45.67.89:27017:baz') == ('123.45.67.89:27017', 'baz')


@pytest.mark.parametrize("argv,expected", [
    ([], {}),
    (['evaluate'], {'cmd': ['evaluate']}),
    (['-u' 'a=5 b=9'], {'update': 'a=5 b=9'}),
    (['-m'], {'mongo_db': 'sacred'}),
])
def test_parse_arguments(argv, expected):
    args = parse_arguments(argv)
    empty = dict(
        update=None,
        config_file=None,
        cmd=[],
        mongo_db=None,
        print_cfg_only=False
    )
    empty.update(expected)

    assert dict(args._get_kwargs()) == empty
