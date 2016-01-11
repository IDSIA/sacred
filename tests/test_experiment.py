#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
"""Global Docstring"""

from mock import patch
import pytest
import sys

from sacred.experiment import Experiment


@pytest.fixture
def ex():
    return Experiment('ator3000')


def test_main(ex):
    @ex.main
    def foo():
        pass

    assert 'foo' in ex.commands
    assert ex.commands['foo'] == foo
    assert ex.default_command == 'foo'


def test_automain_imported(ex):
    main_called = [False]

    with patch.object(sys, 'argv', ['test.py']):

        @ex.automain
        def foo():
            main_called[0] = True

        assert 'foo' in ex.commands
        assert ex.commands['foo'] == foo
        assert ex.default_command == 'foo'
        assert main_called[0] is False


def test_automain_script_runs_main(ex):
    global __name__
    oldname = __name__
    main_called = [False]

    try:
        __name__ = '__main__'
        with patch.object(sys, 'argv', ['test.py']):
            @ex.automain
            def foo():
                main_called[0] = True

            assert 'foo' in ex.commands
            assert ex.commands['foo'] == foo
            assert ex.default_command == 'foo'
            assert main_called[0] is True
    finally:
        __name__ = oldname


def test_fails_on_unused_config_updates(ex):
    @ex.config
    def cfg():
        b = 3
        f = {'oo': 1}
        g = {'a': 'l'}

    @ex.main
    def foo(f, a=10):
        assert f
        return a

    # normal config updates work
    assert ex.run(config_updates={'a': 3, 'b': 2}).result == 3

    # unused config updates raise
    with pytest.raises(KeyError):
        ex.run(config_updates={'c': 3})

    # unused but in config updates work
    ex.run(config_updates={'g': 3})
    ex.run(config_updates={'g': {'a': 'r'}})

    # nested unused config updates raise
    with pytest.raises(KeyError):
        ex.run(config_updates={'g': {'u': 'p'}})

    # nested unused but parent used updates work
    assert ex.run(config_updates={'f': {'uzz': 8}})


