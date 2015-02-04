#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import pytest
from sacred.custom_containers import DogmaticDict, DogmaticList
from sacred.config_scope import ConfigDict

try:
    import numpy as np
except ImportError:
    np = None


@pytest.fixture
def conf_dict():
    cfg = ConfigDict({
        "a": 1,
        "b": 2.0,
        "c": True,
        "d": 'string',
        "e": [1, 2, 3],
        "f": {'a': 'b', 'c': 'd'},
    })
    cfg()
    return cfg


def test_config_dict_is_dict(conf_dict):
    assert isinstance(conf_dict, ConfigDict)
    assert isinstance(conf_dict, dict)


def test_config_dict_contains_keys(conf_dict):
    assert set(conf_dict.keys()) == {'a', 'b', 'c', 'd', 'e', 'f'}

    assert conf_dict['a'] == 1
    assert conf_dict['b'] == 2.0
    assert conf_dict['c']
    assert conf_dict['d'] == 'string'
    assert conf_dict['e'] == [1, 2, 3]
    assert conf_dict['f'] == {'a': 'b', 'c': 'd'}


def test_fixing_values(conf_dict):
    conf_dict({'a': 100})
    assert conf_dict['a'] == 100


def test_fixing_nested_dicts(conf_dict):
    conf_dict({'f': {'c': 't'}})
    assert conf_dict['f']['a'] == 'b'
    assert conf_dict['f']['c'] == 't'


def test_adding_values(conf_dict):
    conf_dict({'g': 23, 'h': {'i': 10}})
    assert conf_dict['g'] == 23
    assert conf_dict['h'] == {'i': 10}
    assert conf_dict.added_values == {'g', 'h', 'h.i'}


def test_typechange(conf_dict):
    conf_dict({'a': 'bar', 'b': 'foo', 'c': 1})
    assert conf_dict.typechanges == {'a': (int, type('bar')),
                                     'b': (float, type('foo')),
                                     'c': (bool, int)}


def test_nested_typechange(conf_dict):
    conf_dict({'f': {'a': 10}})
    assert conf_dict.typechanges == {'f.a': (type('a'), int)}


def is_dogmatic(a):
    if isinstance(a, (DogmaticDict, DogmaticList)):
        return True
    elif isinstance(a, dict):
        return any(is_dogmatic(v) for v in a.values())
    elif isinstance(a, (list, tuple)):
        return any(is_dogmatic(v) for v in a)


def test_conf_dict_is_not_dogmatic(conf_dict):
    conf_dict({'e': [1, 1, 1]})
    assert not is_dogmatic(conf_dict)


@pytest.mark.skipif(np is None, reason="requires numpy")
def test_conf_scope_handles_numpy_bools():
    cfg = ConfigDict({
        "a": np.bool_(1)
    })
    cfg()
    assert 'a' in cfg
    assert cfg['a']


def test_conf_scope_contains_presets():
    cfg = ConfigDict({
        "answer": 42
    })

    cfg(preset={'a': 21, 'unrelated': True})
    assert set(cfg.keys()) == {'a', 'answer', 'unrelated'}
    assert cfg['a'] == 21
    assert cfg['answer'] == 42
    assert cfg['unrelated'] is True


def test_conf_scope_does_not_contain_fallback():
    cfg = ConfigDict({
        "answer": 42
    })

    cfg(fallback={'a': 21, 'b': 10})

    assert set(cfg.keys()) == {'answer'}


def test_fixed_subentry_of_preset():
    cfg = ConfigDict({})

    cfg(preset={'d': {'a': 1, 'b': 2}}, fixed={'d': {'a': 10}})

    assert set(cfg.keys()) == {'d'}
    assert set(cfg['d'].keys()) == {'a', 'b'}
    assert cfg['d']['a'] == 10
    assert cfg['d']['b'] == 2
