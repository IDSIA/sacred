#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import pytest
from sacred.config.custom_containers import DogmaticDict


def test_isinstance_of_dict():
    assert isinstance(DogmaticDict(), dict)


def test_dict_interface_initialized_empty():
    d = DogmaticDict()
    assert d == {}
    assert set(d.keys()) == set()
    assert set(d.values()) == set()
    assert set(d.items()) == set()


def test_dict_interface_set_item():
    d = DogmaticDict()
    d['a'] = 12
    d['b'] = 'foo'
    assert 'a' in d
    assert 'b' in d

    assert d['a'] == 12
    assert d['b'] == 'foo'

    assert set(d.keys()) == {'a', 'b'}
    assert set(d.values()) == {12, 'foo'}
    assert set(d.items()) == {('a', 12), ('b', 'foo')}


def test_dict_interface_del_item():
    d = DogmaticDict()
    d['a'] = 12
    del d['a']
    assert 'a' not in d


def test_dict_interface_update_with_dict():
    d = DogmaticDict()
    d['a'] = 12
    d['b'] = 'foo'

    d.update({'a': 1, 'c': 2})
    assert d['a'] == 1
    assert d['b'] == 'foo'
    assert d['c'] == 2


def test_dict_interface_update_with_kwargs():
    d = DogmaticDict()
    d['a'] = 12
    d['b'] = 'foo'
    d.update(a=2, b=3)
    assert d['a'] == 2
    assert d['b'] == 3


def test_dict_interface_update_with_list_of_items():
    d = DogmaticDict()
    d['a'] = 12
    d['b'] = 'foo'
    d.update([('b', 9), ('c', 7)])
    assert d['a'] == 12
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


def test_fallback():
    d = DogmaticDict(fallback={'a': 23})
    assert 'a' in d
    assert d['a'] == 23
    assert d.get('a') == 23

    d = DogmaticDict()
    d.fallback = {'a': 23}
    assert 'a' in d
    assert d['a'] == 23
    assert d.get('a') == 23


def test_fallback_not_iterated():
    d = DogmaticDict(fallback={'a': 23})
    d['b'] = 1234
    assert list(d.keys()) == ['b']
    assert list(d.values()) == [1234]
    assert list(d.items()) == [('b', 1234)]


def test_overwrite_fallback():
    d = DogmaticDict(fallback={'a': 23})
    d['a'] = 0
    assert d['a'] == 0
    assert list(d.keys()) == ['a']
    assert list(d.values()) == [0]
    assert list(d.items()) == [('a', 0)]


def test_fixed_has_precedence_over_fallback():
    d = DogmaticDict(fixed={'a': 0}, fallback={'a': 23})
    assert d['a'] == 0


def test_nested_fixed_merges_with_fallback():
    d = DogmaticDict(fixed={'foo': {'bar': 20}},
                     fallback={'foo': {'bar': 10, 'c': 5}})
    assert d['foo']['bar'] == 20
    assert d['foo']['c'] == 5


def test_nested_fixed_with_fallback_madness():
    d = DogmaticDict(fixed={'foo': {'bar': 20}},
                     fallback={'foo': {'bar': 10, 'c': 5}})
    d['foo'] = {'bar': 30, 'a': 1}
    assert d['foo']['bar'] == 20
    assert d['foo']['a'] == 1
    assert d['foo']['c'] == 5
