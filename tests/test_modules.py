#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from sacred.config_scope import ConfigScope
from sacred.experiment import Module, Experiment


def test_module_config():
    m = Module("somemod")

    @m.config
    def cfg():
        a = 5
        b = 'foo'

    assert len(m.cfgs) == 1
    cfg = m.cfgs[0]
    assert isinstance(cfg, ConfigScope)
    assert cfg() == {'a': 5, 'b': 'foo'}


def test_module_captured_functions():
    m = Module("somemod")

    @m.capture
    def get_answer(b):
        return b

    assert len(m.captured_functions) == 1
    f = m.captured_functions[0]
    assert f == get_answer


############## Experiment ######################################################

def test_experiment_run():
    ex = Experiment("some_experiment")

    @ex.main
    def main():
        return 12

    assert ex.run() == 12


def test_experiment_run_access_submodule():
    somemod = Module("somemod")

    @somemod.config
    def cfg():
        a = 5
        b = 'foo'

    ex = Experiment("some_experiment", modules=[somemod])

    @ex.main
    def main(somemod):
        return somemod

    r = ex.run()
    assert r['a'] == 5
    assert r['b'] == 'foo'


def test_experiment_run_submodule_function():
    somemod = Module("somemod")

    @somemod.config
    def cfg():
        a = 5
        b = 'foo'

    @somemod.capture
    def get_answer(b):
        return b

    ex = Experiment("some_experiment", modules=[somemod])

    @ex.main
    def main():
        return get_answer()

    assert ex.run() == 'foo'