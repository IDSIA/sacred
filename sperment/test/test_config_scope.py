#!/usr/bin/python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from bunch import Bunch
import unittest
from sperment.config_scope import ConfigScope


########################  Tests  ###############################################

# noinspection PyUnresolvedReferences
class ConfigScopeTest(unittest.TestCase):
    def setUp(self):
        class Cfg(ConfigScope):
            a = 1
            b = 2.0
            c = True
            d = 'string'
            e = [1, 2, 3]
            f = {'a': 'b', 'c': 'd'}

            ignored1 = lambda: 23

            def ignored2(self):
                pass

            ignored3 = int

            class Nested(ConfigScope):
                a = 2

        self.cfg = Cfg

    def test_config_scope_subclass_is_bunch(self):
        self.assertIsInstance(self.cfg, Bunch)

    def test_config_scope_contains_keys(self):
        self.assertSetEqual(set(self.cfg.keys()),
                            {'a', 'b', 'c', 'd', 'e', 'f', 'Nested'})

        self.assertEqual(self.cfg['a'], 1)
        self.assertEqual(self.cfg['b'], 2.0)
        self.assertEqual(self.cfg['c'], True)
        self.assertEqual(self.cfg['d'], 'string')
        self.assertListEqual(self.cfg['e'], [1, 2, 3])
        self.assertDictEqual(self.cfg['f'], {'a': 'b', 'c': 'd'})

    def test_nested_config_scope(self):
        self.assertIsInstance(self.cfg.Nested, Bunch)
        self.assertEqual(self.cfg.Nested.a, 2)