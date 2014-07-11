#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import pytest
from custom_containers import DogmaticDict, DogmaticList
from sacred.config_scope import ConfigScope


@pytest.fixture
def conf_scope():
    @ConfigScope
    def cfg():
        a = 1
        b = 2.0
        c = True
        d = 'string'
        e = [1, 2, 3]
        f = {'a': 'b', 'c': 'd'}
        composit1 = a + b
        composit2 = f['c'] + "ada"

        ignored1 = lambda: 23

        deriv = ignored1()

        def ignored2():
            pass

        ignored3 = int

    cfg()
    return cfg


def test_config_scope_is_dict(conf_scope):
    assert isinstance(conf_scope, ConfigScope)
    assert isinstance(conf_scope, dict)


def test_config_scope_contains_keys(conf_scope):
    assert set(conf_scope.keys()) == {'a', 'b', 'c', 'd', 'e', 'f',
                                      'composit1', 'composit2', 'deriv'}

    assert conf_scope['a'] == 1
    assert conf_scope['b'] == 2.0
    assert conf_scope['c']
    assert conf_scope['d'] == 'string'
    assert conf_scope['e'] == [1, 2, 3]
    assert conf_scope['f'] == {'a': 'b', 'c': 'd'}
    assert conf_scope['composit1'] == 3.0
    assert conf_scope['composit2'] == 'dada'
    assert conf_scope['deriv'] == 23


def test_fixing_values(conf_scope):
    conf_scope({'a': 100})
    assert conf_scope['a'] == 100
    assert conf_scope['composit1'] == 102.0


def test_fixing_nested_dicts(conf_scope):
    conf_scope({'f': {'c': 't'}})
    assert conf_scope['f']['a'] == 'b'
    assert conf_scope['f']['c'] == 't'
    assert conf_scope['composit2'] == 'tada'


def test_adding_values(conf_scope):
    conf_scope({'g': 23, 'h': {'i': 10}})
    assert conf_scope['g'] == 23
    assert conf_scope['h'] == {'i': 10}
    assert conf_scope.added_values == {'g', 'h', 'h.i'}


def test_typechange(conf_scope):
    conf_scope({'a': 'bar', 'b': 'foo', 'c': 1})
    assert conf_scope.typechanges == {'a': (int, type('bar')),
                                      'b': (float, type('foo')),
                                      'c': (bool, int)}


def test_nested_typechange(conf_scope):
    conf_scope({'f': {'a': 10}})
    assert conf_scope.typechanges == {'f.a': (type('a'), int)}


def is_dogmatic(a):
    if isinstance(a, (DogmaticDict, DogmaticList)):
        return True
    elif isinstance(a, dict):
        return any(is_dogmatic(v) for v in a.values())
    elif isinstance(a, (list, tuple)):
        return any(is_dogmatic(v) for v in a)


def test_conf_scope_is_not_dogmatic(conf_scope):
    conf_scope({'e': [1, 1, 1]})
    assert not is_dogmatic(conf_scope)