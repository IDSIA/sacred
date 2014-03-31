#!/usr/bin/python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import unittest
from sperment.signature import Signature


##############  function definitions to test on ################################
def foo():
    return


def bariza(a, b, c):
    return a, b, c


def complex_function_name(a=1, b='fo', c=9):
    return a, b, c


def FunCTIonWithCAPItals(a, b, c=3, **kwargs):
    return a, b, c, kwargs


def _name_with_underscore_(fo, bar, *baz):
    return fo, bar, baz


def __double_underscore__(man, o, *men, **oo):
    return man, o, men, oo


def old_name(verylongvariablename):
    return verylongvariablename


def generic(*args, **kwargs):
    return args, kwargs


def onlykwrgs(**kwargs):
    return kwargs


renamed = old_name

functions = [foo, bariza, complex_function_name, FunCTIonWithCAPItals,
             _name_with_underscore_, __double_underscore__, old_name, renamed]


########################  Tests  ###############################################
class SignatureTest(unittest.TestCase):
    def test_constructor_extract_function_name(self):
        names = ['foo', 'bariza', 'complex_function_name',
                 'FunCTIonWithCAPItals', '_name_with_underscore_',
                 '__double_underscore__', 'old_name', 'old_name']
        for f, name in zip(functions, names):
            s = Signature(f)
            self.assertEqual(s.name, name,
                             " on %s expect %s but was %s" % (
                                 f.__name__, name, s.name))

    def test_constructor_extracts_all_arguments(self):
        arguments = [[], ['a', 'b', 'c'], ['a', 'b', 'c'], ['a', 'b', 'c'],
                         ['fo', 'bar'], ['man', 'o'], ['verylongvariablename'],
                         ['verylongvariablename']]
        for f, args in zip(functions, arguments):
            s = Signature(f)
            self.assertSequenceEqual(s.arguments, args,
                                     " on %s expect %s but was %s" % (
                                         f.__name__, args, s.arguments))

    def test_constructor_extract_vararg_name(self):
        vararg_names = [None, None, None, None, 'baz', 'men', None, None]
        for f, varg in zip(functions, vararg_names):
            s = Signature(f)
            self.assertEqual(s.vararg_name, varg,
                             " on %s expect %s but was %s" % (
                                 f.__name__, varg, s.vararg_name))

    def test_constructor_extract_kwargs_wildcard_name(self):
        kw_wc_names = [None, None, None, 'kwargs', None, 'oo', None, None]
        for f, kw_wc in zip(functions, kw_wc_names):
            s = Signature(f)
            self.assertEqual(s.kw_wildcard_name, kw_wc,
                             " on %s expect %s but was %s" % (
                                 f.__name__, kw_wc, s.kw_wildcard_name))

    def test_constructor_extract_positional_arguments(self):
        pos_args = [[], ['a', 'b', 'c'], [], ['a', 'b'], ['fo', 'bar'],
                    ['man', 'o'], ['verylongvariablename']]
        for f, pargs in zip(functions, pos_args):
            s = Signature(f)
            self.assertEqual(s.positional_args, pargs,
                             " on %s expect %s but was %s" % (
                                 f.__name__, pargs, s.positional_args))

    def test_constructor_extract_kwargs(self):
        kwarg_list = [{}, {}, {'a': 1, 'b': 'fo', 'c': 9}, {'c': 3}, {}, {}, {}]
        for f, kwargs in zip(functions, kwarg_list):
            s = Signature(f)
            self.assertEqual(s.kwargs, kwargs,
                             " on %s expect %s but was %s" % (
                                 f.__name__, kwargs, s.kwargs))

    def test_get_free_parameters(self):
        free = Signature(foo).get_free_parameters([], {})
        self.assertEqual(free, [])
        free = Signature(bariza).get_free_parameters([], {'c': 3})
        self.assertEqual(free, ['a', 'b'])
        free = Signature(complex_function_name).get_free_parameters([], {})
        self.assertEqual(free, ['a', 'b', 'c'])
        free = Signature(_name_with_underscore_).get_free_parameters([], {})
        self.assertEqual(free, ['fo', 'bar'])
        s = Signature(__double_underscore__)
        self.assertEqual(s.get_free_parameters([1, 2, 3], {}), [])

    def test_construct_arguments_with_unexpected_kwargs_raises_typeerror(self):
        kwargs = {'zimbabwe': 23}
        regex = ".*unexpected.*zimbabwe.*"
        with self.assertRaisesRegexp(TypeError, regex):
            Signature(foo).construct_arguments([], kwargs, {})
        with self.assertRaisesRegexp(TypeError, regex):
            Signature(bariza).construct_arguments([], kwargs, {})
        with self.assertRaisesRegexp(TypeError, regex):
            s = Signature(complex_function_name)
            s.construct_arguments([], kwargs, {})
        with self.assertRaisesRegexp(TypeError, regex):
            s = Signature(_name_with_underscore_)
            s.construct_arguments([], kwargs, {})
        with self.assertRaisesRegexp(TypeError, regex):
            Signature(old_name).construct_arguments([], kwargs, {})
        with self.assertRaisesRegexp(TypeError, regex):
            Signature(renamed).construct_arguments([], kwargs, {})

    def test_construct_arguments_with_unexpected_args_raises_typeerror(self):
        regex = ".*unexpected.*"
        with self.assertRaisesRegexp(TypeError, regex):
            Signature(foo).construct_arguments([1], {}, {})
        with self.assertRaisesRegexp(TypeError, regex):
            Signature(bariza).construct_arguments([1, 2, 3, 4], {}, {})
        with self.assertRaisesRegexp(TypeError, regex):
            s = Signature(complex_function_name)
            s.construct_arguments([1, 2, 3, 4], {}, {})
        with self.assertRaisesRegexp(TypeError, regex):
            Signature(old_name).construct_arguments([1, 2], {}, {})
        with self.assertRaisesRegexp(TypeError, regex):
            Signature(renamed).construct_arguments([1, 2], {}, {})

    def test_construct_arguments_with_varargs_doesnt_raise(self):
        Signature(generic).construct_arguments([1, 2, 3], {}, {})
        Signature(__double_underscore__).construct_arguments(
            [1, 2, 3, 4, 5], {}, {})
        Signature(_name_with_underscore_).construct_arguments(
            [1, 2, 3, 4], {}, {})
        self.assertTrue(True)

    def test_construct_arguments_with_kwargswildcard_doesnt_raise(self):
        kwargs = {'zimbabwe': 23}
        Signature(FunCTIonWithCAPItals).construct_arguments(
            [1, 2, 3], kwargs, {})
        Signature(__double_underscore__).construct_arguments([1, 2], kwargs, {})
        self.assertTrue(True)

    def test_construct_arguments_with_expected_kwargs_does_not_raise(self):
        s = Signature(complex_function_name)
        s.construct_arguments([], {'a': 4, 'b': 3, 'c': 2}, {})
        s = Signature(FunCTIonWithCAPItals)
        s.construct_arguments([1, 2], {'c': 5}, {})
        self.assertTrue(True)

    def test_construct_arguments_with_kwargs_for_posargs_does_not_raise(self):
        Signature(bariza).construct_arguments([], {'a': 4, 'b': 3, 'c': 2}, {})
        s = Signature(FunCTIonWithCAPItals)
        s.construct_arguments([], {'a': 4, 'b': 3, 'c': 2, 'd': 6}, {})
        self.assertTrue(True)

    def test_construct_arguments_with_duplicate_args_raises_typeerror(self):
        regex = ".*multiple values.*"
        with self.assertRaisesRegexp(TypeError, regex):
            s = Signature(bariza)
            s.construct_arguments([1, 2, 3], {'a': 4, 'b': 5}, {})

        with self.assertRaisesRegexp(TypeError, regex):
            s = Signature(complex_function_name)
            s.construct_arguments([1], {'a': 4}, {})

        with self.assertRaisesRegexp(TypeError, regex):
            s = Signature(FunCTIonWithCAPItals)
            s.construct_arguments([1, 2, 3], {'c': 6}, {})

    def test_construct_arguments_without_duplicates_passes(self):
        s = Signature(bariza)
        s.construct_arguments([1, 2], {'c': 5}, {})

        s = Signature(complex_function_name)
        s.construct_arguments([1], {'b': 4}, {})

        s = Signature(FunCTIonWithCAPItals)
        s.construct_arguments([], {'a': 6, 'b': 6, 'c': 6}, {})
        self.assertTrue(True)

    def test_construct_arguments_without_options_returns_same_args_kwargs(self):
        s = Signature(foo)
        args, kwargs = s.construct_arguments([], {}, {})
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})

        s = Signature(bariza)
        args, kwargs = s.construct_arguments([2, 4, 6], {}, {})
        self.assertEqual(args, [2, 4, 6])
        self.assertEqual(kwargs, {})

        s = Signature(complex_function_name)
        args, kwargs = s.construct_arguments([2], {'c': 6, 'b': 7}, {})
        self.assertEqual(args, [2])
        self.assertEqual(kwargs, {'c': 6, 'b': 7})

        s = Signature(_name_with_underscore_)
        args, kwargs = s.construct_arguments([], {'fo': 7, 'bar': 6}, {})
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {'fo': 7, 'bar': 6})

    def test_construct_arguments_completes_kwargs_from_options(self):
        s = Signature(bariza)
        args, kwargs = s.construct_arguments([2, 4], {}, {'c': 6})
        self.assertEqual(args, [2, 4])
        self.assertEqual(kwargs, {'c': 6})

        s = Signature(complex_function_name)
        args, kwargs = s.construct_arguments([], {'c': 6, 'b': 7}, {'a': 1})
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {'a': 1, 'c': 6, 'b': 7})

        s = Signature(_name_with_underscore_)
        args, kwargs = s.construct_arguments([], {}, {'fo': 7, 'bar': 6})
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {'fo': 7, 'bar': 6})

    def test_construct_arguments_ignores_excess_options(self):
        s = Signature(bariza)
        args, kwargs = s.construct_arguments([2], {'b': 4},
                                             {'c': 6, 'foo': 9, 'bar': 0})
        self.assertEqual(args, [2])
        self.assertEqual(kwargs, {'b': 4, 'c': 6})

    def test_construct_arguments_does_not_overwrite_args_and_kwargs(self):
        s = Signature(bariza)
        args, kwargs = s.construct_arguments([1, 2], {'c': 3},
                                             {'a': 6, 'b': 6, 'c': 6})
        self.assertEqual(args, [1, 2])
        self.assertEqual(kwargs, {'c': 3})

    def test_construct_arguments_overwrites_defaults(self):
        s = Signature(complex_function_name)
        args, kwargs = s.construct_arguments([], {}, {'a': 11, 'b': 12, 'c': 7})
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {'a': 11, 'b': 12, 'c': 7})

    def test_construct_arguments_raises_if_args_unfilled(self):
        s = Signature(bariza)
        regex = ".*missing.*"
        with self.assertRaisesRegexp(TypeError, regex):
            s.construct_arguments([], {}, {})
        with self.assertRaisesRegexp(TypeError, regex):
            s.construct_arguments([1, 2], {}, {})
        with self.assertRaisesRegexp(TypeError, regex):
            s.construct_arguments([1], {'b': 3}, {})
        with self.assertRaisesRegexp(TypeError, regex):
            s.construct_arguments([1], {'c': 5}, {})

    def test_construct_arguments_does_not_raise_if_all_args_filled(self):
        s = Signature(bariza)
        s.construct_arguments([1, 2, 3], {}, {})
        s.construct_arguments([1, 2], {'c': 6}, {})
        s.construct_arguments([1], {'b': 6, 'c': 6}, {})
        s.construct_arguments([], {'a': 6, 'b': 6, 'c': 6}, {})
        self.assertTrue(True)

    def test_construct_arguments_does_not_raise_for_missing_defaults(self):
        s = Signature(complex_function_name)
        s.construct_arguments([], {}, {})
        self.assertTrue(True)

    def test_unicode_(self):
        self.assertEqual(Signature(foo).__unicode__(),
                         "foo()")
        self.assertEqual(Signature(bariza).__unicode__(),
                         "bariza(a, b, c)")
        self.assertRegexpMatches(Signature(complex_function_name).__unicode__(),
                                 "complex_function_name\(a=1, b=u?'fo', c=9\)")
        self.assertEqual(Signature(FunCTIonWithCAPItals).__unicode__(),
                         "FunCTIonWithCAPItals(a, b, c=3, **kwargs)")
        self.assertEqual(Signature(_name_with_underscore_).__unicode__(),
                         "_name_with_underscore_(fo, bar, *baz)")
        self.assertEqual(Signature(__double_underscore__).__unicode__(),
                         "__double_underscore__(man, o, *men, **oo)")
        self.assertEqual(Signature(old_name).__unicode__(),
                         "old_name(verylongvariablename)")
        self.assertEqual(Signature(renamed).__unicode__(),
                         "old_name(verylongvariablename)")
        self.assertEqual(Signature(generic).__unicode__(),
                         "generic(*args, **kwargs)")
        self.assertEqual(Signature(onlykwrgs).__unicode__(),
                         "onlykwrgs(**kwargs)")

    def test_repr_(self):
        regex = "<Signature at 0x[0-9a-fA-F]+ for '%s'>"
        self.assertRegexpMatches(Signature(foo).__repr__(),
                                 regex % "foo")
        self.assertRegexpMatches(Signature(bariza).__repr__(),
                                 regex % "bariza")
        self.assertRegexpMatches(Signature(complex_function_name).__repr__(),
                                 regex % "complex_function_name")
        self.assertRegexpMatches(Signature(FunCTIonWithCAPItals).__repr__(),
                                 regex % "FunCTIonWithCAPItals")
        self.assertRegexpMatches(Signature(_name_with_underscore_).__repr__(),
                                 regex % "_name_with_underscore_")
        self.assertRegexpMatches(Signature(__double_underscore__).__repr__(),
                                 regex % "__double_underscore__")
        self.assertRegexpMatches(Signature(old_name).__repr__(),
                                 regex % "old_name")
        self.assertRegexpMatches(Signature(renamed).__repr__(),
                                 regex % "old_name")
        self.assertRegexpMatches(Signature(generic).__repr__(),
                                 regex % "generic")
        self.assertRegexpMatches(Signature(onlykwrgs).__repr__(),
                                 regex % "onlykwrgs")
