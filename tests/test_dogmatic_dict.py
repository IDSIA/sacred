#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from sacred.config_scope import DogmaticDict


def test_isinstance_of_dict():
    assert isinstance(DogmaticDict(), dict)


def test_dict_interface():
    d = DogmaticDict()
    assert d == {}
    d['a'] = 12
    d['b'] = 'foo'
    assert 'a' in d
    assert 'b' in d

    assert d['a'] == 12
    assert d['b'] == 'foo'

    assert set(d.keys()) == {'a', 'b'}
    assert set(d.values()) == {12, 'foo'}
    assert set(d.items()) == {('a', 12), ('b', 'foo')}

    del d['a']
    assert 'a' not in d

    d['b'] = 'bar'
    assert d['b'] == 'bar'

    d.update({'a': 1, 'c': 2})
    assert d['a'] == 1
    assert d['b'] == 'bar'
    assert d['c'] == 2

    d.update(a=2, b=3)
    assert d['a'] == 2
    assert d['b'] == 3
    assert d['c'] == 2

    d.update([('b', 9), ('c', 7)])
    assert d['a'] == 2
    assert d['b'] == 9
    assert d['c'] == 7


def test_fixed_value_not_initialized():
    d = DogmaticDict({'a': 7})
    assert 'a' not in d


def test_fixed_value_fixed():
    d = DogmaticDict({'a': 7})
    d['a'] = 8
    assert d['a'] == 7

    del d['a']
    assert 'a' in d
    assert d['a'] == 7

    d.update([('a', 9), ('b', 12)])
    assert d['a'] == 7

    d.update({'a': 9, 'b': 12})
    assert d['a'] == 7

    d.update(a=10, b=13)
    assert d['a'] == 7


def test_revelation():
    d = DogmaticDict({'a': 7, 'b': 12})
    d['b'] = 23
    assert 'a' not in d
    m = d.revelation()
    assert set(m) == {'a'}
    assert 'a' in d