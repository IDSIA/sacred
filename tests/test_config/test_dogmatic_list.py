#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import pytest
from sacred.config.custom_containers import DogmaticDict, DogmaticList


def test_isinstance_of_list():
    assert isinstance(DogmaticList(), list)


def test_init():
    l = DogmaticList()
    assert l == []

    l2 = DogmaticList([2, 3, 1])
    assert l2 == [2, 3, 1]


def test_append():
    l = DogmaticList([1, 2])
    l.append(3)
    l.append(4)
    assert l == [1, 2]


def test_extend():
    l = DogmaticList([1, 2])
    l.extend([3, 4])
    assert l == [1, 2]


def test_insert():
    l = DogmaticList([1, 2])
    l.insert(1, 17)
    assert l == [1, 2]


def test_pop():
    l = DogmaticList([1, 2, 3])
    with pytest.raises(TypeError):
        l.pop()
    assert l == [1, 2, 3]


def test_sort():
    l = DogmaticList([3, 1, 2])
    l.sort()
    assert l == [3, 1, 2]


def test_reverse():
    l = DogmaticList([1, 2, 3])
    l.reverse()
    assert l == [1, 2, 3]


def test_setitem():
    l = DogmaticList([1, 2, 3])
    l[1] = 23
    assert l == [1, 2, 3]


def test_setslice():
    l = DogmaticList([1, 2, 3])
    l[1:3] = [4, 5]
    assert l == [1, 2, 3]


def test_delitem():
    l = DogmaticList([1, 2, 3])
    del l[1]
    assert l == [1, 2, 3]


def test_delslice():
    l = DogmaticList([1, 2, 3])
    del l[1:]
    assert l == [1, 2, 3]


def test_iadd():
    l = DogmaticList([1, 2])
    l += [3, 4]
    assert l == [1, 2]


def test_imul():
    l = DogmaticList([1, 2])
    l *= 4
    assert l == [1, 2]


def test_list_interface_getitem():
    l = DogmaticList([0, 1, 2])
    assert l[0] == 0
    assert l[1] == 1
    assert l[2] == 2

    assert l[-1] == 2
    assert l[-2] == 1
    assert l[-3] == 0


def test_list_interface_len():
    l = DogmaticList()
    assert len(l) == 0
    l = DogmaticList([0, 1, 2])
    assert len(l) == 3


def test_list_interface_count():
    l = DogmaticList([1, 2, 4, 4, 5])
    assert l.count(1) == 1
    assert l.count(3) == 0
    assert l.count(4) == 2


def test_list_interface_index():
    l = DogmaticList([1, 2, 4, 4, 5])
    assert l.index(1) == 0
    assert l.index(4) == 2
    assert l.index(5) == 4
    with pytest.raises(ValueError):
        l.index(3)


def test_empty_revelation():
    l = DogmaticList([1, 2, 3])
    assert l.revelation() == set()


def test_nested_dict_revelation():
    d1 = DogmaticDict({'a': 7, 'b': 12})
    d2 = DogmaticDict({'c': 7})
    l = DogmaticList([d1, 2, d2])
#    assert l.revelation() == {'0.a', '0.b', '2.c'}
    l.revelation()
    assert 'a' in l[0]
    assert 'b' in l[0]
    assert 'c' in l[2]
