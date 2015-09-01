#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from sacred.config.config_scope import ConfigScope
from sacred.experiment import Experiment, Ingredient


def test_ingredient_config():
    m = Ingredient("somemod")

    @m.config
    def cfg():
        a = 5
        b = 'foo'

    assert len(m.configurations) == 1
    cfg = m.configurations[0]
    assert isinstance(cfg, ConfigScope)
    assert cfg() == {'a': 5, 'b': 'foo'}


def test_ingredient_captured_functions():
    m = Ingredient("somemod")

    @m.capture
    def get_answer(b):
        return b

    assert len(m.captured_functions) == 1
    f = m.captured_functions[0]
    assert f == get_answer


def test_ingredient_command():
    m = Ingredient("somemod")

    m.add_config(a=42, b='foo{}')

    @m.command
    def transmogrify(a, b):
        return b.format(a)

    assert 'transmogrify' in m.commands
    assert m.commands['transmogrify'] == transmogrify
    ex = Experiment('foo', ingredients=[m])

    assert ex.run_command('somemod.transmogrify').result == 'foo42'


# ############# Experiment ####################################################

def test_experiment_run():
    ex = Experiment("some_experiment")

    @ex.main
    def main():
        return 12

    assert ex.run().result == 12


def test_experiment_run_access_subingredient():
    somemod = Ingredient("somemod")

    @somemod.config
    def cfg():
        a = 5
        b = 'foo'

    ex = Experiment("some_experiment", ingredients=[somemod])

    @ex.main
    def main(somemod):
        return somemod

    r = ex.run().result
    assert r['a'] == 5
    assert r['b'] == 'foo'


def test_experiment_run_subingredient_function():
    somemod = Ingredient("somemod")

    @somemod.config
    def cfg():
        a = 5
        b = 'foo'

    @somemod.capture
    def get_answer(b):
        return b

    ex = Experiment("some_experiment", ingredients=[somemod])

    @ex.main
    def main():
        return get_answer()

    assert ex.run().result == 'foo'
