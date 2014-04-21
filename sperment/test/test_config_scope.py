#!/usr/bin/python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import unittest
from sperment.config_scope import ConfigScope, DogmaticDict


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
        self.cfg({'f': {'c': 't'}})
        self.assertEqual(self.cfg['f']['a'], 'b')
        self.assertEqual(self.cfg['f']['c'], 't')
        self.assertEqual(self.cfg['composit2'], 'tada')


class DogmaticDictTests(unittest.TestCase):
    def test_isinstance_of_dict(self):
        self.assertIsInstance(DogmaticDict(), dict)

    def test_dict_interface(self):
        d = DogmaticDict()
        d['a'] = 12
        d['b'] = 'foo'
        self.assertIn('a', d)
        self.assertIn('b', d)
        self.assertEqual(d['a'], 12)
        self.assertEqual(d['b'], 'foo')
        self.assertSetEqual(set(d.keys()), {'a', 'b'})
        self.assertSetEqual(set(d.values()), {12, 'foo'})
        self.assertSetEqual(set(d.items()), {('a', 12), ('b', 'foo')})

        del d['a']
        self.assertNotIn('a', d)

        d['b'] = 'bar'
        self.assertEqual(d['b'], 'bar')

        d.update({'a': 1, 'c': 2})
        self.assertEqual(d['a'], 1)
        self.assertEqual(d['b'], 'bar')
        self.assertEqual(d['c'], 2)

        d.update(a=2, b=3)
        self.assertEqual(d['a'], 2)
        self.assertEqual(d['b'], 3)
        self.assertEqual(d['c'], 2)

        d.update([('b', 9), ('c', 7)])
        self.assertEqual(d['a'], 2)
        self.assertEqual(d['b'], 9)
        self.assertEqual(d['c'], 7)

    def test_fixed_value_not_initialized(self):
        d = DogmaticDict({'a': 7})
        self.assertNotIn('a', d)

    def test_fixed_value_fixed(self):
        d = DogmaticDict({'a': 7})
        d['a'] = 8
        self.assertEqual(d['a'], 7)

        del d['a']
        self.assertIn('a', d)
        self.assertEqual(d['a'], 7)

        d.update([('a', 9), ('b', 12)])
        self.assertEqual(d['a'], 7)

        d.update({'a': 9, 'b': 12})
        self.assertEqual(d['a'], 7)

        d.update(a=10, b=13)
        self.assertEqual(d['a'], 7)

    def test_revelation(self):
        d = DogmaticDict({'a': 7, 'b': 12})
        d['b'] = 23
        self.assertNotIn('a', d)
        m = d.revelation()
        self.assertSetEqual(set(m), {'a'})
        self.assertIn('a', d)
