#!/usr/bin/env python3
# coding=utf-8
from copy import copy, deepcopy

import pytest

from sacred.config.path import Path

valid_path_examples = [
    # ('', ('',)),
    ('foo', ('foo',)),
    ('_f_90b00_', ('_f_90b00_',)),
    ('foo.bar', ('foo', 'bar')),
    ('a.bb.c3._d4', ('a', 'bb', 'c3', '_d4')),
    ('a[2]', ('a', 2)),
    ('[18]', (18,)),
    ('a[18][True][(1, 2)].foo', ('a', 18, True, (1, 2), 'foo')),
]


@pytest.mark.parametrize("path, parts", valid_path_examples)
def test_parsing(path, parts):
    p = Path.from_str(path)
    assert p.parts == parts
    assert repr(p) == 'p"' + path + '"'
    assert len(p) == len(parts)


@pytest.mark.parametrize("path, parts", valid_path_examples)
def test_hash(path, parts):
    assert hash(Path(*parts)) == hash(path)


@pytest.mark.parametrize("path, parts", valid_path_examples)
def test_eq(path, parts):
    p = Path(*parts)
    assert p == p
    assert p == path


def test_gt():
    assert Path(0, 5) > Path(0, 4)
    assert Path('abc') > Path('aaa')


def test_lt():
    assert Path(0, 2) < Path(0, 4)
    assert Path('aaa') < Path('abc')


def test_sort():
    assert sorted([Path(7), Path(19), Path(1)]) == [Path(1), Path(7), Path(19)]
    assert sorted([Path('c'), Path('b'), Path('a')]) == [Path('a'), Path('b'), Path('c')]


def test_add():
    assert Path('foo') + Path('bar') == Path('foo', 'bar')
    assert Path('foo') + 'bar[2]' == Path('foo', 'bar', 2)
    assert 'foo.bar' + Path(2, 'b') == Path('foo', 'bar', 2, 'b')


def test_copy():
    p = Path(1, 'foo', True)
    q = copy(p)
    assert p == q
    assert p is not q


def test_deepcopy():
    p = Path(1, 'foo', True)
    q = deepcopy(p)
    assert p == q
    assert p is not q
