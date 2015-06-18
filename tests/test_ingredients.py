#!/usr/bin/env python
# coding=utf-8
"""global docstring"""
from __future__ import division, print_function, unicode_literals

import tempfile
import json
import pytest
from sacred.config import ConfigScope, ConfigDict

from sacred.dependencies import Source, PackageDependency
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


def test_add_config_dict(ing):
    ing.add_config({'foo': 12, 'bar': 4})
    assert len(ing.configurations) == 1
    assert isinstance(ing.configurations[0], ConfigDict)
    assert ing.configurations[0]() == {'foo': 12, 'bar': 4}


def test_add_config_kwargs(ing):
    ing.add_config(foo=18, bar=3)
    assert len(ing.configurations) == 1
    assert isinstance(ing.configurations[0], ConfigDict)
    assert ing.configurations[0]() == {'foo': 18, 'bar': 3}


def test_add_config_kwargs_and_dict_raises(ing):
    with pytest.raises(ValueError):
        ing.add_config({'foo': 12}, bar=3)


def test_add_config_empty_raises(ing):
    with pytest.raises(ValueError):
        ing.add_config()


def test_add_config_non_dict_raises(ing):
    with pytest.raises(TypeError):
        ing.add_config(12)

    with pytest.raises(TypeError):
        ing.add_config('foo')


def test_add_config_file(ing):
    with tempfile.NamedTemporaryFile('w+', suffix='.json') as f:
        json.dump({'foo': 15, 'bar': 7}, f)
        f.flush()
        f.seek(0)  # simulates closing and reopening
        ing.add_config_file(f.name)

    assert len(ing.configurations) == 1
    assert isinstance(ing.configurations[0], ConfigDict)
    assert ing.configurations[0]() == {'foo': 15, 'bar': 7}


def test_add_config_file_nonexisting_raises(ing):
    with pytest.raises(IOError):
        ing.add_config_file("nonexistens.json")


def test_add_source_file(ing):
    with tempfile.NamedTemporaryFile('w+', suffix='.py') as f:
        f.write("print('Hello World')")
        f.flush()
        f.seek(0)  # simulates closing and reopening
        ing.add_source_file(f.name)
        assert Source.create(f.name) in ing.sources


def test_add_source_file_nonexisting_raises(ing):
    with pytest.raises(ValueError):
        ing.add_source_file('nonexisting.py')


def test_add_package_dependency(ing):
    ing.add_package_dependency('django', '1.8.2')
    assert PackageDependency('django', '1.8.2') in ing.dependencies


def test_add_package_dependency_invalid_version_raises(ing):
    with pytest.raises(ValueError):
        ing.add_package_dependency('django', 'foobar')
