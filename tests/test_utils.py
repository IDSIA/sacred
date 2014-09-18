#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from sacred.utils import (recursive_update, iterate_separately,
                          iterate_flattened, set_by_dotted_path,
                          get_by_dotted_path, iter_path_splits, iter_prefixes,
                          join_paths, is_prefix, convert_to_nested_dict)


def test_recursive_update():
    d = {'a': {'b': 1}}
    res = recursive_update(d, {'c': 2, 'a': {'d': 3}})
    assert d is res
    assert res == {'a': {'b': 1, 'd': 3}, 'c': 2}


def test_iterate_separately():
    d = {'a1': 1, 'b2': {'foo': 'bar'}, 'c1': 'f', 'd1': [1, 2, 3], 'e2': {}}
    res = list(iterate_separately(d))
    assert res == [('a1', 1), ('c1', 'f'), ('d1', [1, 2, 3]),
                   ('b2', {'foo': 'bar'}), ('e2', {})]


def test_iterate_flattened():
    d = {'a': {'aa': 1, 'ab': {'aba': 8}}, 'b': 3}
    assert list(iterate_flattened(d)) == \
        [('a.aa', 1), ('a.ab.aba', 8), ('b', 3)]


def test_set_by_dotted_path():
    d = {'foo': {'bar': 7}}
    set_by_dotted_path(d, 'foo.bar', 10)
    assert d == {'foo': {'bar': 10}}


def test_set_by_dotted_path_creates_missing_dicts():
    d = {'foo': {'bar': 7}}
    set_by_dotted_path(d, 'foo.d.baz', 3)
    assert d == {'foo': {'bar': 7, 'd': {'baz': 3}}}


def test_get_by_dotted_path():
    assert get_by_dotted_path({'a': 12}, 'a') == 12
    assert get_by_dotted_path({'a': 12}, '') == {'a': 12}
    assert get_by_dotted_path({'foo': {'a': 12}}, 'foo.a') == 12
    assert get_by_dotted_path({'foo': {'a': 12}}, 'foo.b') is None


def test_iter_path_splits():
    assert list(iter_path_splits('foo.bar.baz')) ==\
        [('',        'foo.bar.baz'),
         ('foo',     'bar.baz'),
         ('foo.bar', 'baz')]


def test_iter_prefixes():
    assert list(iter_prefixes('foo.bar.baz')) == \
        ['foo', 'foo.bar', 'foo.bar.baz']


def test_join_paths():
    assert join_paths() == ''
    assert join_paths('foo') == 'foo'
    assert join_paths('foo', 'bar') == 'foo.bar'
    assert join_paths('a', 'b', 'c', 'd') == 'a.b.c.d'
    assert join_paths('', 'b', '', 'd') == 'b.d'
    assert join_paths('a.b', 'c.d.e') == 'a.b.c.d.e'
    assert join_paths('a.b.', 'c.d.e') == 'a.b.c.d.e'


def test_is_prefix():
    assert is_prefix('', 'foo')
    assert is_prefix('foo', 'foo.bar')
    assert is_prefix('foo.bar', 'foo.bar.baz')

    assert not is_prefix('a', 'foo.bar')
    assert not is_prefix('a.bar', 'foo.bar')
    assert not is_prefix('foo.b', 'foo.bar')
    assert not is_prefix('foo.bar', 'foo.bar')


def test_convert_to_nested_dict():
    dotted_dict = {'foo.bar': 8, 'foo.baz': 7}
    assert convert_to_nested_dict(dotted_dict) == {'foo': {'bar': 8, 'baz': 7}}


def test_convert_to_nested_dict_nested():
    dotted_dict = {'a.b': {'foo.bar': 8},  'a.b.foo.baz': 7}
    assert convert_to_nested_dict(dotted_dict) == \
           {'a': {'b': {'foo': {'bar': 8, 'baz': 7}}}}