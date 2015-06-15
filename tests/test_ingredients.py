#!/usr/bin/env python
# coding=utf-8
"""global docstring"""
from __future__ import division, print_function, unicode_literals

import pytest
from sacred.config import ConfigScope

from sacred.dependencies import Source
from sacred.experiment import Ingredient


@pytest.fixture
def ing():
    return Ingredient('tickle')


def test_create_ingredient(ing):
    assert ing.path == 'tickle'
    assert ing.doc == __doc__
    assert Source.create(__file__) in ing.sources


def test_capture_function(ing):
    @ing.capture
    def foo(something):
        pass
    assert foo in ing.captured_functions
    assert foo.prefix is None


def test_capture_function_with_prefix(ing):
    @ing.capture(prefix='bar')
    def foo(something):
        pass
    assert foo in ing.captured_functions
    assert foo.prefix == 'bar'


def test_capture_function_twice(ing):
    @ing.capture
    def foo(something):
        pass

    assert ing.captured_functions == [foo]
    ing.capture(foo)
    assert ing.captured_functions == [foo]


def test_add_pre_run_hook(ing):
    @ing.pre_run_hook
    def foo(something):
        pass
    assert foo in ing.pre_run_hooks
    assert foo in ing.captured_functions
    assert foo.prefix is None


def test_add_pre_run_hook_with_prefix(ing):
    @ing.pre_run_hook(prefix='bar')
    def foo(something):
        pass
    assert foo in ing.pre_run_hooks
    assert foo in ing.captured_functions
    assert foo.prefix == 'bar'


def test_add_post_run_hook(ing):
    @ing.post_run_hook
    def foo(something):
        pass
    assert foo in ing.post_run_hooks
    assert foo in ing.captured_functions
    assert foo.prefix is None


def test_add_post_run_hook_with_prefix(ing):
    @ing.post_run_hook(prefix='bar')
    def foo(something):
        pass
    assert foo in ing.post_run_hooks
    assert foo in ing.captured_functions
    assert foo.prefix == 'bar'


def test_add_command(ing):
    @ing.command
    def foo(a, b):
        pass

    assert 'foo' in ing.commands
    assert ing.commands['foo'] == foo
    assert foo.prefix is None


def test_add_command_with_prefix(ing):
    @ing.command(prefix='bar')
    def foo(a, b):
        pass

    assert 'foo' in ing.commands
    assert ing.commands['foo'] == foo
    assert foo.prefix == 'bar'


def test_add_config_hook(ing):
    def foo(config, command_name, logger):
        pass
    ch = ing.config_hook(foo)
    assert ch == foo
    assert foo in ing.config_hooks


def test_add_config(ing):
    @ing.config
    def cfg():
        pass

    assert isinstance(cfg, ConfigScope)
    assert cfg in ing.configurations


def test_add_named_config(ing):
    @ing.named_config
    def foo():
        pass
    assert isinstance(foo, ConfigScope)
    assert 'foo' in ing.named_configs
    assert ing.named_configs['foo'] == foo


def test_add_config_hook_with_invalid_signature_raises(ing):
    with pytest.raises(ValueError):
        @ing.config_hook
        def foo(wrong, signature):
            pass
