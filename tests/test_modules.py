#!/usr/bin/python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import pytest
from sacred import Module, Experiment
from sacred.experiment import CircularDependencyError


@pytest.fixture
def somemod():
    m = Module("somemod")

    @m.config
    def cfg():
        a = 5
        b = 'foo'

    @m.capture
    def get_answer(b):
        return b

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


############## Experiment ######################################################

def test_experiment_run():
    ex = Experiment("some_experiment")

    @ex.main
    def main():
        return 12

    assert ex.run().result == 12


def test_experiment_run_access_submodule(somemod):
    ex = Experiment("some_experiment", modules=[somemod])

    @ex.main
    def main(somemod):
        return somemod

    assert ex.run().result == {'a': 5, 'b': 'foo'}


def test_experiment_run_submodule_function(somemod):
    ex = Experiment("some_experiment", modules=[somemod])

    @ex.main
    def main():
        return somemod.get_answer()

    assert ex.run().result == 'foo'