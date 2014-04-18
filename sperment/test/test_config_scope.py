#!/usr/bin/python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import unittest
from sperment.config_scope import ConfigScope


########################  Tests  ###############################################

# noinspection PyUnresolvedReferences
class ConfigScopeTest(unittest.TestCase):
    def setUp(self):

        @ConfigScope
        def cfg():
            a = 1
            b = 2.0
            c = True
            d = 'string'
            e = [1, 2, 3]
            f = {'a': 'b', 'c': 'd'}
            composit1 = a + b
            composit2 = f['c'] + "ada"

            ignored1 = lambda: 23

            deriv = ignored1()

            def ignored2(self):
                pass

            ignored3 = int

        self.cfg = cfg
        self.cfg()

    def test_config_scope_is_config_scope(self):
        self.assertIsInstance(self.cfg, ConfigScope)

    def test_config_scope_contains_keys(self):
        self.assertSetEqual(set(self.cfg.keys()),
                            {'a', 'b', 'c', 'd', 'e', 'f', 'composit1', 'composit2', 'deriv'})

        self.assertEqual(self.cfg['a'], 1)
        self.assertEqual(self.cfg['b'], 2.0)
        self.assertEqual(self.cfg['c'], True)
        self.assertEqual(self.cfg['d'], 'string')
        self.assertListEqual(self.cfg['e'], [1, 2, 3])
        self.assertDictEqual(self.cfg['f'], {'a': 'b', 'c': 'd'})
        self.assertEqual(self.cfg['composit1'], 3.0)
        self.assertEqual(self.cfg['composit2'], 'dada')
        self.assertEqual(self.cfg['deriv'], 23)

    def test_fixing_values(self):
        self.cfg({'a': 100})
        self.assertEqual(self.cfg['a'], 100)
        self.assertEqual(self.cfg['composit1'], 102.0)

    def test_fixing_nested_dicts(self):
        self.cfg({'f': {'b': 'ZZ', 'c': 't'}})
        self.assertEqual(self.cfg['f']['a'], 'b')
        self.assertEqual(self.cfg['f']['b'], 'ZZ')
        self.assertEqual(self.cfg['f']['c'], 't')
        self.assertEqual(self.cfg['composit2'], 'tada')

