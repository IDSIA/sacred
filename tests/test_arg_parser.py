#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
import pytest
from sacred.arg_parser import parse_mongo_db_arg, parse_arguments


def test_parse_mongo_db_arg():
    assert parse_mongo_db_arg('foo') == ('localhost:27017', 'foo')


def test_parse_mongo_db_arg_hostname():
    assert parse_mongo_db_arg('localhost:28017') == \
        ('localhost:28017', 'sacred')

    assert parse_mongo_db_arg('www.mymongo.db:28017') == \
        ('www.mymongo.db:28017', 'sacred')

    assert parse_mongo_db_arg('123.45.67.89:27017') == \
        ('123.45.67.89:27017', 'sacred')


def test_parse_mongo_db_arg_hostname_dbname():
    assert parse_mongo_db_arg('localhost:28017:foo') == \
        ('localhost:28017', 'foo')

    assert parse_mongo_db_arg('www.mymongo.db:28017:bar') == \
        ('www.mymongo.db:28017', 'bar')

    assert parse_mongo_db_arg('123.45.67.89:27017:baz') == \
        ('123.45.67.89:27017', 'baz')


@pytest.mark.parametrize("argv,expected", [
    ([],                                {}),
    (['evaluate'],                      {'cmd': ['evaluate']}),
    (['evaluate', '1', '2', '3'],       {'cmd': ['evaluate', '1', '2', '3']}),
    (['-u' 'a=5 b=9'],                  {'update': 'a=5 b=9'}),
    (['--update', 'a=7 b=6'],           {'update': 'a=7 b=6'}),
    (['-m'],                            {'mongo_db': 'sacred'}),
    (['--mongo_db'],                    {'mongo_db': 'sacred'}),
    (['-m', 'localhost:27018'],         {'mongo_db': 'localhost:27018'}),
    (['--mongo_db', 'localhost:27018'], {'mongo_db': 'localhost:27018'}),
    (['-p'],                            {'print_cfg_only': True}),
    (['--print_cfg_only'],              {'print_cfg_only': True}),
    (['-c', 'foo.json'],                {'config_file': 'foo.json'}),
    (['--config_file', 'foo.json'],     {'config_file': 'foo.json'}),
])
def test_parse_individual_arguments(argv, expected):
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


def test_parse_compound_arglist1():
    argv = ['eval', '1', '17', '-u', 'a=17 b=1', '-m', '-p']
    args = parse_arguments(argv)
    expected = dict(
        update='a=17 b=1',
        config_file=None,
        cmd=['eval', '1', '17'],
        mongo_db='sacred',
        print_cfg_only=True
    )
    assert dict(args._get_kwargs()) == expected


def test_parse_compound_arglist2():
    argv = ['-m', 'localhost:1111', '-u', 'a=foo', '-c', 'foo.json']
    args = parse_arguments(argv)
    expected = dict(
        update='a=foo',
        config_file='foo.json',
        cmd=[],
        mongo_db='localhost:1111',
        print_cfg_only=False
    )
    assert dict(args._get_kwargs()) == expected