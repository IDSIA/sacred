#!/usr/bin/python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import pytest
from sacred import Module
from sacred.experiment import CircularDependencyError


@pytest.fixture
def somemod():
    m = Module("somemod")

    @m.config
    def cfg():
        a = 5
        b = 'foo'
    return m


def test_module_config(somemod):
    d = somemod.set_up_config()
    assert d == {'a': 5, 'b': 'foo'}


def test_submodule_config(somemod):
    m = Module("mod", modules=[somemod])
    d = m.set_up_config()
    assert d == {'somemod': {'a': 5, 'b': 'foo'}}


def test_submodule_config_renamed(somemod):
    m = Module("mod")
    m.modules["foo"] = somemod
    d = m.set_up_config()
    assert d == {'foo': {'a': 5, 'b': 'foo'}}


def test_submodule_config_with_update(somemod):
    m = Module("mod", modules=[somemod])
    d = m.set_up_config(config_updates={'somemod': {'a': 13}})
    assert d == {'somemod': {'a': 13, 'b': 'foo'}}


def test_submodule_circle_raises(somemod):
    m = Module("mod", modules=[somemod])
    somemod.modules['parent'] = m
    with pytest.raises(CircularDependencyError) as excinfo:
        d = m.set_up_config(config_updates={'somemod': {'a': 13}})
