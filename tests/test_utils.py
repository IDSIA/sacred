#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import os
import sys
import tempfile

import pytest

from sacred.utils import (PATHCHANGE, convert_to_nested_dict,
                          get_by_dotted_path, is_prefix, is_subdir,
                          iter_path_splits, iter_prefixes, iterate_flattened,
                          iterate_flattened_separately, join_paths,
                          recursive_update, set_by_dotted_path, get_inheritors,
                          convert_camel_case_to_snake_case, tee_output,
                          apply_backspaces_and_linefeeds)


def test_recursive_update():
    d = {'a': {'b': 1}}
    res = recursive_update(d, {'c': 2, 'a': {'d': 3}})
    assert d is res
    assert res == {'a': {'b': 1, 'd': 3}, 'c': 2}


def test_iterate_flattened_separately():
    d = {'a1': 1,
         'b2': {'bar': 'foo', 'foo': 'bar'},
         'c1': 'f',
         'd1': [1, 2, 3],
         'e2': {}}
    res = list(iterate_flattened_separately(d, ['foo', 'bar']))
    assert res == [('a1', 1), ('c1', 'f'), ('d1', [1, 2, 3]), ('e2', {}),
                   ('b2', PATHCHANGE), ('b2.foo', 'bar'), ('b2.bar', 'foo')]


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
        [('', 'foo.bar.baz'),
         ('foo', 'bar.baz'),
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
    dotted_dict = {'a.b': {'foo.bar': 8}, 'a.b.foo.baz': 7}
    assert convert_to_nested_dict(dotted_dict) == \
        {'a': {'b': {'foo': {'bar': 8, 'baz': 7}}}}


@pytest.mark.parametrize('path,parent,expected', [
    ('/var/test2', '/var/test', False),
    ('/var/test', '/var/test2', False),
    ('var/test2', 'var/test', False),
    ('var/test', 'var/test2', False),
    ('/var/test/sub', '/var/test', True),
    ('/var/test', '/var/test/sub', False),
    ('var/test/sub', 'var/test', True),
    ('var/test', 'var/test', True),
    ('var/test', 'var/test/fake_sub/..', True),
    ('var/test/sub/sub2/sub3/../..', 'var/test', True),
    ('var/test/sub', 'var/test/fake_sub/..', True),
    ('var/test', 'var/test/sub', False)
])
def test_is_subdirectory(path, parent, expected):
    assert is_subdir(path, parent) == expected


def test_get_inheritors():
    class A(object):
        pass

    class B(A):
        pass

    class C(B):
        pass

    class D(A):
        pass

    class E(object):
        pass

    assert get_inheritors(A) == {B, C, D}


@pytest.mark.parametrize('name,expected', [
    ('CamelCase', 'camel_case'),
    ('snake_case', 'snake_case'),
    ('CamelCamelCase', 'camel_camel_case'),
    ('Camel2Camel2Case', 'camel2_camel2_case'),
    ('getHTTPResponseCode', 'get_http_response_code'),
    ('get2HTTPResponseCode', 'get2_http_response_code'),
    ('HTTPResponseCode', 'http_response_code'),
    ('HTTPResponseCodeXYZ', 'http_response_code_xyz')
])
def test_convert_camel_case_to_snake_case(name, expected):
    assert convert_camel_case_to_snake_case(name) == expected


@pytest.mark.parametrize('text,expected', [
    ('', ''),
    ('\b', ''),
    ('\r', ''),
    ('ab\bc', 'ac'),
    ('\ba', 'a'),
    ('ab\nc\b\bd', 'ab\nd'),
    ('abc\rdef', 'def'),
    ('abc\r', 'abc'),
    ('abc\rd', 'dbc'),
    ('abc\r\nd', 'abc\nd'),
    ('abc\ndef\rg', 'abc\ngef'),
    ('abc\ndef\r\rg', 'abc\ngef')
])
def test_apply_backspaces_and_linefeeds(text, expected):
    assert apply_backspaces_and_linefeeds(text) == expected


def test_tee_output(capsys):
    from sacred.optional import libc

    expected_lines = {
        "captured stdout\n",
        "captured stderr\n",
        "and this is from echo\n"}
    if not sys.platform.startswith('win'):
        # FIXME: this line randomly doesn't show on windows (skip for now)
        expected_lines.add("stdout from C\n")

    with capsys.disabled():
        try:
            print('before (stdout)')
            print('before (stderr)')
            with tempfile.NamedTemporaryFile(delete=False) as f, tee_output(f):
                print("captured stdout")
                print("captured stderr")
                if not sys.platform.startswith('win'):
                    libc.puts(b'stdout from C')
                    libc.fflush(None)
                os.system('echo and this is from echo')

            print('after (stdout)')
            print('after (stderr)')

            with open(f.name, 'r') as f:
                lines = set(f.readlines())
                assert lines == expected_lines
        finally:
            print('deleting', f.name)
            os.remove(f.name)
