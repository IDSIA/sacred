#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
import pytest
from sacred.arg_parser import (parse_mongo_db_arg, get_config_updates,
                               parse_args)


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
    ('',                 {}),
    ('run',              {'run': True}),
    ('with 1 2',         {'with': True, 'UPDATE': ['1', '2']}),
    ('evaluate',         {'COMMAND': 'evaluate'}),
    ('help',             {'help': True}),
    ('help evaluate',    {'help': True, 'COMMAND': 'evaluate'}),
    ('-m foo',           {'--mongo_db': 'foo'}),
    ('--mongo_db=bar',   {'--mongo_db': 'bar'}),
])
def test_parse_individual_arguments(argv, expected):
    args = parse_args(['test_prog.py'] + argv.split())
    plain = {
        '--help': False,
        '--mongo_db': None,
        'COMMAND': None,
        'UPDATE': [],
        'help': False,
        'run': False,
        'with': False
    }
    plain.update(expected)

    assert args == plain


def test_parse_compound_arglist1():
    argv = "run with a=17 b=1 -m localhost:22222".split()
    args = parse_args(['test_prog.py'] + argv)
    expected = {
        '--help': False,
        '--mongo_db': 'localhost:22222',
        'COMMAND': None,
        'UPDATE': ['a=17', 'b=1'],
        'help': False,
        'run': True,
        'with': True
    }
    assert args == expected


def test_parse_compound_arglist2():
    argv = "evaluate with a=18 b=2".split()
    args = parse_args(['test_prog.py'] + argv)
    expected = {
        '--help': False,
        '--mongo_db': None,
        'COMMAND': 'evaluate',
        'UPDATE': ['a=18', 'b=2'],
        'help': False,
        'run': False,
        'with': True
    }
    assert args == expected


@pytest.mark.parametrize("update,expected", [
    (None,              {}),
    (['a=5'],           {'a': 5}),
    (['foo.bar=6'],     {'foo': {'bar': 6}}),
    (['a=7 b=8'],       {'a': 7, 'b': 8}),
    (['a=7; b=8;'],     {'a': 7, 'b': 8}),
    (['a=9', 'b=0'],    {'a': 9, 'b': 0}),
    (['a=9;', 'b=0;'],  {'a': 9, 'b': 0}),
    (["hello='world'"], {'hello': 'world'}),
    (['hello="world"'], {'hello': 'world'}),
    (["f=23.5"],        {'f': 23.5}),
    (["n=None"],        {'n': None}),
    (["t=True"],        {'t': True}),
    (["f=False"],       {'f': False}),
])
def test_get_config_updates(update, expected):
    assert get_config_updates(update) == expected