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


def test_experiment_named_config_subingredient():
    somemod = Ingredient("somemod")

    @somemod.config
    def sub_cfg():
        a = 15

    @somemod.capture
    def get_answer(a):
        return a

    @somemod.named_config
    def nsubcfg():
        a = 16

    ex = Experiment("some_experiment", ingredients=[somemod])

    @ex.config
    def cfg():
        a = 1

    @ex.named_config
    def ncfg():
        a = 2
        somemod = {'a': 25}

    @ex.main
    def main(a):
        return a, get_answer()

    assert ex.run().result == (1, 15)
    assert ex.run(named_configs=['somemod.nsubcfg']).result == (1, 16)
    assert ex.run(named_configs=['ncfg']).result == (2, 25)
    assert ex.run(named_configs=['ncfg', 'somemod.nsubcfg']).result == (2, 16)
    assert ex.run(named_configs=['somemod.nsubcfg', 'ncfg']).result == (2, 25)


def test_experiment_named_config_subingredient_overwrite():
    somemod = Ingredient("somemod")

    @somemod.capture
    def get_answer(a):
        return a

    ex = Experiment("some_experiment", ingredients=[somemod])

    @ex.named_config
    def ncfg():
        somemod = {'a': 1}

    @ex.main
    def main():
        return get_answer()

    assert ex.run(named_configs=['ncfg']).result == 1
    assert ex.run(config_updates={'somemod': {'a': 2}}).result == 2
    assert ex.run(named_configs=['ncfg'],
                  config_updates={'somemod': {'a': 2}}
                  ).result == 2


def test_experiment_double_named_config():
    ex = Experiment()

    @ex.config
    def config():
        a = 0
        d = {
            'e': 0,
            'f': 0
        }

    @ex.named_config
    def A():
        a = 2
        d = {
            'e': 2,
            'f': 2
        }

    @ex.named_config
    def B():
        d = {'f': -1}

    @ex.main
    def run(a, d):
        return a, d['e'], d['f']

    assert ex.run().result == (0, 0, 0)
    assert ex.run(named_configs=['A']).result == (2, 2, 2)
    assert ex.run(named_configs=['B']).result == (0, 0, -1)
    assert ex.run(named_configs=['A', 'B']).result == (2, 2, -1)
    assert ex.run(named_configs=['B', 'A']).result == (2, 2, 2)


def test_double_nested_config():
    sub_sub_ing = Ingredient('sub_sub_ing')
    sub_ing = Ingredient('sub_ing', [sub_sub_ing])
    ing = Ingredient('ing', [sub_ing])
    ex = Experiment('ex', [ing])

    @ex.config
    def config():
        a = 1
        seed = 42

    @ing.config
    def config():
        b = 1

    @sub_ing.config
    def config():
        c = 2

    @sub_sub_ing.config
    def config():
        d = 3

    @sub_sub_ing.capture
    def sub_sub_ing_main(_config):
        assert _config == {
            'd': 3
        }, _config

    @sub_ing.capture
    def sub_ing_main(_config):
        assert _config == {
            'c': 2,
            'sub_sub_ing': {'d': 3}
        }, _config

    @ing.capture
    def ing_main(_config):
        assert _config == {
            'b': 1,
            'sub_sub_ing': {'d': 3},
            'sub_ing': {'c': 2}
        }, _config

    @ex.main
    def main(_config):
        assert _config == {
            'a': 1,
            'sub_sub_ing': {'d': 3},
            'sub_ing': {'c': 2},
            'ing': {'b': 1},
            'seed': 42
        }, _config

        ing_main()
        sub_ing_main()
        sub_sub_ing_main()

    ex.run()
