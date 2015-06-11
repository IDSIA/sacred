#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import pytest
from sacred.config import ConfigScope, chain_evaluate_config_scopes


def test_chained_config_scopes_contain_combined_keys():
    @ConfigScope
    def cfg1():
        a = 10

    @ConfigScope
    def cfg2():
        b = 20

    final_cfg, summary = chain_evaluate_config_scopes([cfg1, cfg2])
    assert set(final_cfg.keys()) == {'a', 'b'}
    assert final_cfg['a'] == 10
    assert final_cfg['b'] == 20


def test_chained_config_scopes_can_access_previous_keys():
    @ConfigScope
    def cfg1():
        a = 10

    @ConfigScope
    def cfg2(a):
        b = 2 * a

    final_cfg, summary = chain_evaluate_config_scopes([cfg1, cfg2])
    assert set(final_cfg.keys()) == {'a', 'b'}
    assert final_cfg['a'] == 10


def test_chained_config_scopes_can_modify_previous_keys():
    @ConfigScope
    def cfg1():
        a = 10
        b = 20

    @ConfigScope
    def cfg2(a):
        a *= 2
        b = 22

    final_cfg, summary = chain_evaluate_config_scopes([cfg1, cfg2])
    assert set(final_cfg.keys()) == {'a', 'b'}
    assert final_cfg['a'] == 20
    assert final_cfg['b'] == 22


def test_chained_config_scopes_raise_for_undeclared_previous_keys():
    @ConfigScope
    def cfg1():
        a = 10

    @ConfigScope
    def cfg2():
        b = a * 2

    with pytest.raises(NameError):
        chain_evaluate_config_scopes([cfg1, cfg2])


def test_chained_config_scopes_cannot_modify_fixed():
    @ConfigScope
    def cfg1():
        c = 10
        a = c * 2

    @ConfigScope
    def cfg2(c):
        b = 4 * c
        c *= 3

    final_cfg, summary = chain_evaluate_config_scopes([cfg1, cfg2],
                                                      fixed={'c': 5})
    assert set(final_cfg.keys()) == {'a', 'b', 'c'}
    assert final_cfg['a'] == 10
    assert final_cfg['b'] == 20
    assert final_cfg['c'] == 5


def test_chained_config_scopes_can_access_preset():
    @ConfigScope
    def cfg1(c):
        a = 10 + c

    @ConfigScope
    def cfg2(a, c):
        b = a * 2 + c

    final_cfg, summary = chain_evaluate_config_scopes([cfg1, cfg2],
                                                      preset={'c': 32})
    assert set(final_cfg.keys()) == {'a', 'b', 'c'}
    assert final_cfg['a'] == 42
    assert final_cfg['b'] == 116
    assert final_cfg['c'] == 32


def test_chained_config_scopes_can_access_fallback():
    @ConfigScope
    def cfg1(c):
        a = 10 + c

    @ConfigScope
    def cfg2(a, c):
        b = a * 2 + c

    final_cfg, summary = chain_evaluate_config_scopes([cfg1, cfg2],
                                                      fallback={'c': 32})
    assert set(final_cfg.keys()) == {'a', 'b'}
    assert final_cfg['a'] == 42
    assert final_cfg['b'] == 116


def test_chained_config_scopes_fix_subentries():
    @ConfigScope
    def cfg1():
        d = {
            'a': 10,
            'b': 20
        }

    @ConfigScope
    def cfg2():
        pass

    final_cfg, summary = chain_evaluate_config_scopes([cfg1, cfg2],
                                                      fixed={'d': {'a': 0}})
    assert set(final_cfg['d'].keys()) == {'a', 'b'}
    assert final_cfg['d']['a'] == 0
    assert final_cfg['d']['b'] == 20


def test_empty_chain_contains_preset_and_fixed():
    final_cfg, summary = chain_evaluate_config_scopes([],
                                                      fixed={'a': 0},
                                                      preset={'a': 1, 'b': 2})
    assert set(final_cfg.keys()) == {'a', 'b'}
    assert final_cfg['a'] == 0
    assert final_cfg['b'] == 2
