#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import pytest
from sacred.config.custom_containers import FallbackDict


@pytest.fixture
def fbdict():
    return FallbackDict({'fall1': 7, 'fall3': True})


def test_is_dictionary(fbdict):
    assert isinstance(fbdict, dict)


def test_getitem(fbdict):
    assert 'foo' not in fbdict
    fbdict['foo'] = 23
    assert 'foo' in fbdict
    assert fbdict['foo'] == 23


def test_fallback(fbdict):
    assert 'fall1' in fbdict
    assert fbdict['fall1'] == 7
    fbdict['fall1'] = 8
    assert fbdict['fall1'] == 8


def test_get(fbdict):
    fbdict['a'] = 'b'
    assert fbdict.get('a', 18) == 'b'
    assert fbdict.get('fall1', 18) == 7
    assert fbdict.get('notexisting', 18) == 18
    assert fbdict.get('fall3', 18) is True


@pytest.mark.parametrize('method',
                         ['items', 'iteritems', 'iterkeys', 'itervalues',
                          'keys', 'popitem', 'update', 'values', 'viewitems',
                          'viewkeys', 'viewvalues', '__iter__', '__len__'])
def test_not_implemented(method, fbdict):
    with pytest.raises(NotImplementedError):
        getattr(fbdict, method)()


def test_special_not_implemented(fbdict):
    with pytest.raises(NotImplementedError):
        fbdict.pop('fall1')
    with pytest.raises(NotImplementedError):
        fbdict.setdefault('fall2', None)
