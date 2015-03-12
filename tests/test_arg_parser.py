#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals

import pytest
from sacred.arg_parser import (_convert_value, _parse_mongo_db_arg,
                               get_config_updates, parse_args)


def test_parse_mongo_db_arg():
    assert _parse_mongo_db_arg('foo') == ('localhost:27017', 'foo', '')

def test_parse_mongo_db_arg_collection():
    assert _parse_mongo_db_arg('foo.bar') == ('localhost:27017', 'foo', 'bar')


def test_parse_mongo_db_arg_hostname():
    assert _parse_mongo_db_arg('localhost:28017') == \
        ('localhost:28017', 'sacred', '')

    assert _parse_mongo_db_arg('www.mymongo.db:28017') == \
        ('www.mymongo.db:28017', 'sacred', '')

    assert _parse_mongo_db_arg('123.45.67.89:27017') == \
        ('123.45.67.89:27017', 'sacred', '')


def test_parse_mongo_db_arg_hostname_dbname():
    assert _parse_mongo_db_arg('localhost:28017:foo') == \
        ('localhost:28017', 'foo', '')

    assert _parse_mongo_db_arg('www.mymongo.db:28017:bar') == \
        ('www.mymongo.db:28017', 'bar', '')

    assert _parse_mongo_db_arg('123.45.67.89:27017:baz') == \
        ('123.45.67.89:27017', 'baz', '')


def test_parse_mongo_db_arg_hostname_dbname_collection_name():
    assert _parse_mongo_db_arg('localhost:28017:foo.bar') == \
        ('localhost:28017', 'foo', 'bar')

    assert _parse_mongo_db_arg('www.mymongo.db:28017:bar.baz') == \
        ('www.mymongo.db:28017', 'bar', 'baz')

    assert _parse_mongo_db_arg('123.45.67.89:27017:baz.foo') == \
        ('123.45.67.89:27017', 'baz', 'foo')

@pytest.mark.parametrize("argv,expected", [
    ('',                 {}),
    ('run',              {'COMMAND': 'run'}),
    ('with 1 2',         {'with': True, 'UPDATE': ['1', '2']}),
    ('evaluate',         {'COMMAND': 'evaluate'}),
    ('help',             {'help': True}),
    ('help evaluate',    {'help': True, 'COMMAND': 'evaluate'}),
    ('-h',               {'--help': True}),
    ('--help',           {'--help': True}),
    ('-m foo',           {'--mongo_db': 'foo'}),
    ('--mongo_db=bar',   {'--mongo_db': 'bar'}),
    ('-l 10',            {'--logging': '10'}),
    ('--logging=30',     {'--logging': '30'}),
])
def test_parse_individual_arguments(argv, expected):
    args = parse_args(['test_prog.py'] + argv.split(), print_help=False)
    plain = {
        '--help': False,
        '--mongo_db': None,
        '--logging': None,
        'COMMAND': None,
        'UPDATE': [],
        'help': False,
        'with': False,
        '--debug': False
    }
    plain.update(expected)

    assert args == plain


def test_parse_compound_arglist1():
    argv = "run with a=17 b=1 -m localhost:22222".split()
    args = parse_args(['test_prog.py'] + argv)
    expected = {
        '--help': False,
        '--mongo_db': 'localhost:22222',
        '--logging': None,
        '--debug': False,
        'COMMAND': 'run',
        'UPDATE': ['a=17', 'b=1'],
        'help': False,
        'with': True
    }
    assert args == expected


def test_parse_compound_arglist2():
    argv = "evaluate with a=18 b=2 -l30".split()
    args = parse_args(['test_prog.py'] + argv)
    expected = {
        '--help': False,
        '--mongo_db': None,
        '--logging': '30',
        '--debug': False,
        'COMMAND': 'evaluate',
        'UPDATE': ['a=18', 'b=2'],
        'help': False,
        'with': True
    }
    assert args == expected


@pytest.mark.parametrize("update,expected", [
    (None,              {}),
    (['a=5'],           {'a': 5}),
    (['foo.bar=6'],     {'foo': {'bar': 6}}),
    (['a=9', 'b=0'],    {'a': 9, 'b': 0}),
    (["hello='world'"], {'hello': 'world'}),
    (['hello="world"'], {'hello': 'world'}),
    (["f=23.5"],        {'f': 23.5}),
    (["n=None"],        {'n': None}),
    (["t=True"],        {'t': True}),
    (["f=False"],       {'f': False}),
])
def test_get_config_updates(update, expected):
    assert get_config_updates(update) == (expected, [])


@pytest.mark.parametrize("value,expected", [
    ('None',          None),
    ('True',          True),
    ('False',         False),
    ('246',           246),
    ('1.0',           1.0),
    ('1.',            1.0),
    ('.1',            0.1),
    ('1e3',           1e3),
    ('-.4e-12',       -0.4e-12),
    ('-.4e-12',       -0.4e-12),
    ('[1,2,3]',       [1, 2, 3]),
    ('[1.,.1]', [1., .1]),
    ('[True, False]', [True, False]),
    ('[None, None]', [None, None]),
    ('[1.0,2.0,3.0]', [1.0, 2.0, 3.0]),
    ('{"a":1}', {'a': 1}),
    ('{"foo":1, "bar":2.0}', {'foo': 1, 'bar': 2.0}),
    ('{"a":1., "b":.2}', {'a': 1., 'b': .2}),
    ('{"a":True, "b":False}', {'a': True, 'b': False}),
    ('{"a":None}', {'a': None}),
    ('{"a":[1, 2.0, True, None], "b":"foo"}', {"a": [1, 2.0, True, None],
                                               "b": "foo"}),
    ('bob', 'bob'),
    ('"hello world"', 'hello world'),
    ("'hello world'", 'hello world'),
])
def test_convert_value(value, expected):
    assert _convert_value(value) == expected
