#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function

import re

import pytest
from sacred.config.signature import Signature


# #############  function definitions to test on ##############################
def foo():
    return


def bariza(a, b, c):
    return a, b, c


def complex_function_name(a=1, b='fo', c=9):
    return a, b, c


# noinspection PyPep8Naming
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

ids = ['foo', 'bariza', 'complex_function_name', 'FunCTIonWithCAPItals',
       '_name_with_underscore_', '__double_underscore__', 'old_name',
       'renamed']

names = ['foo', 'bariza', 'complex_function_name', 'FunCTIonWithCAPItals',
         '_name_with_underscore_', '__double_underscore__', 'old_name',
         'old_name']

arguments = [[], ['a', 'b', 'c'], ['a', 'b', 'c'], ['a', 'b', 'c'],
             ['fo', 'bar'], ['man', 'o'], ['verylongvariablename'],
             ['verylongvariablename']]

vararg_names = [None, None, None, None, 'baz', 'men', None, None]

kw_wc_names = [None, None, None, 'kwargs', None, 'oo', None, None]

pos_arguments = [[], ['a', 'b', 'c'], [], ['a', 'b'], ['fo', 'bar'],
                 ['man', 'o'], ['verylongvariablename'],
                 ['verylongvariablename']]

kwarg_list = [{}, {}, {'a': 1, 'b': 'fo', 'c': 9}, {'c': 3}, {}, {}, {}, {}]


class SomeClass(object):
    def bla(self, a, b, c):
        return a, b, c


# #######################  Tests  #############################################

@pytest.mark.parametrize("function, name", zip(functions, names), ids=ids)
def test_constructor_extract_function_name(function, name):
        s = Signature(function)
        assert s.name == name


@pytest.mark.parametrize("function, args", zip(functions, arguments), ids=ids)
def test_constructor_extracts_all_arguments(function, args):
        s = Signature(function)
        assert s.arguments == args


@pytest.mark.parametrize("function, vararg", zip(functions, vararg_names),
                         ids=ids)
def test_constructor_extract_vararg_name(function, vararg):
        s = Signature(function)
        assert s.vararg_name == vararg


@pytest.mark.parametrize("function, kw_wc", zip(functions, kw_wc_names),
                         ids=ids)
def test_constructor_extract_kwargs_wildcard_name(function, kw_wc):
        s = Signature(function)
        assert s.kw_wildcard_name == kw_wc


@pytest.mark.parametrize("function, pos_args", zip(functions, pos_arguments),
                         ids=ids)
def test_constructor_extract_positional_arguments(function, pos_args):
        s = Signature(function)
        assert s.positional_args == pos_args


@pytest.mark.parametrize("function, kwargs",
                         zip(functions, kwarg_list),
                         ids=ids)
def test_constructor_extract_kwargs(function, kwargs):
        s = Signature(function)
        assert s.kwargs == kwargs


def test_get_free_parameters():
    free = Signature(foo).get_free_parameters([], {})
    assert free == []
    free = Signature(bariza).get_free_parameters([], {'c': 3})
    assert free == ['a', 'b']
    free = Signature(complex_function_name).get_free_parameters([], {})
    assert free == ['a', 'b', 'c']
    free = Signature(_name_with_underscore_).get_free_parameters([], {})
    assert free == ['fo', 'bar']
    s = Signature(__double_underscore__)
    assert s.get_free_parameters([1, 2, 3], {}) == []


@pytest.mark.parametrize('function',
                         [foo, bariza, complex_function_name,
                          _name_with_underscore_, old_name, renamed])
def test_construct_arguments_with_unexpected_kwargs_raises_typeerror(function):
    kwargs = {'zimbabwe': 23}
    unexpected = re.compile(".*unexpected.*zimbabwe.*")
    with pytest.raises(TypeError) as excinfo:
        Signature(function).construct_arguments([], kwargs, {})
    assert unexpected.match(excinfo.value.args[0])


@pytest.mark.parametrize('func,args', [
    (foo, [1]),
    (bariza, [1, 2, 3, 4]),
    (complex_function_name, [1, 2, 3, 4]),
    (old_name, [1, 2]),
    (renamed, [1, 2])
])
def test_construct_arguments_with_unexpected_args_raises_typeerror(func, args):
    unexpected = re.compile(".*unexpected.*")
    with pytest.raises(TypeError) as excinfo:
        Signature(func).construct_arguments(args, {}, {})
    assert unexpected.match(excinfo.value.args[0])


def test_construct_arguments_with_varargs_doesnt_raise():
    Signature(generic).construct_arguments([1, 2, 3], {}, {})
    Signature(__double_underscore__).construct_arguments(
        [1, 2, 3, 4, 5], {}, {})
    Signature(_name_with_underscore_).construct_arguments(
        [1, 2, 3, 4], {}, {})


def test_construct_arguments_with_kwargswildcard_doesnt_raise():
    kwargs = {'zimbabwe': 23}
    Signature(FunCTIonWithCAPItals).construct_arguments(
        [1, 2, 3], kwargs, {})
    Signature(__double_underscore__).construct_arguments([1, 2], kwargs, {})


def test_construct_arguments_with_expected_kwargs_does_not_raise():
    s = Signature(complex_function_name)
    s.construct_arguments([], {'a': 4, 'b': 3, 'c': 2}, {})
    s = Signature(FunCTIonWithCAPItals)
    s.construct_arguments([1, 2], {'c': 5}, {})


def test_construct_arguments_with_kwargs_for_posargs_does_not_raise():
    Signature(bariza).construct_arguments([], {'a': 4, 'b': 3, 'c': 2}, {})
    s = Signature(FunCTIonWithCAPItals)
    s.construct_arguments([], {'a': 4, 'b': 3, 'c': 2, 'd': 6}, {})


def test_construct_arguments_with_duplicate_args_raises_typeerror():
    multiple_values = re.compile(".*multiple values.*")
    with pytest.raises(TypeError) as excinfo:
        s = Signature(bariza)
        s.construct_arguments([1, 2, 3], {'a': 4, 'b': 5}, {})
    assert multiple_values.match(excinfo.value.args[0])
    with pytest.raises(TypeError) as excinfo:
        s = Signature(complex_function_name)
        s.construct_arguments([1], {'a': 4}, {})
    assert multiple_values.match(excinfo.value.args[0])
    with pytest.raises(TypeError) as excinfo:
        s = Signature(FunCTIonWithCAPItals)
        s.construct_arguments([1, 2, 3], {'c': 6}, {})
    assert multiple_values.match(excinfo.value.args[0])


def test_construct_arguments_without_duplicates_passes():
    s = Signature(bariza)
    s.construct_arguments([1, 2], {'c': 5}, {})

    s = Signature(complex_function_name)
    s.construct_arguments([1], {'b': 4}, {})

    s = Signature(FunCTIonWithCAPItals)
    s.construct_arguments([], {'a': 6, 'b': 6, 'c': 6}, {})


def test_construct_arguments_without_options_returns_same_args_kwargs():
    s = Signature(foo)
    args, kwargs = s.construct_arguments([], {}, {})
    assert args == []
    assert kwargs == {}

    s = Signature(bariza)
    args, kwargs = s.construct_arguments([2, 4, 6], {}, {})
    assert args == [2, 4, 6]
    assert kwargs == {}

    s = Signature(complex_function_name)
    args, kwargs = s.construct_arguments([2], {'c': 6, 'b': 7}, {})
    assert args == [2]
    assert kwargs == {'c': 6, 'b': 7}

    s = Signature(_name_with_underscore_)
    args, kwargs = s.construct_arguments([], {'fo': 7, 'bar': 6}, {})
    assert args == []
    assert kwargs == {'fo': 7, 'bar': 6}


def test_construct_arguments_completes_kwargs_from_options():
    s = Signature(bariza)
    args, kwargs = s.construct_arguments([2, 4], {}, {'c': 6})
    assert args == [2, 4]
    assert kwargs == {'c': 6}
    s = Signature(complex_function_name)
    args, kwargs = s.construct_arguments([], {'c': 6, 'b': 7}, {'a': 1})
    assert args == []
    assert kwargs == {'a': 1, 'c': 6, 'b': 7}

    s = Signature(_name_with_underscore_)
    args, kwargs = s.construct_arguments([], {}, {'fo': 7, 'bar': 6})
    assert args == []
    assert kwargs == {'fo': 7, 'bar': 6}


def test_construct_arguments_ignores_excess_options():
    s = Signature(bariza)
    args, kwargs = s.construct_arguments([2], {'b': 4},
                                         {'c': 6, 'foo': 9, 'bar': 0})
    assert args == [2]
    assert kwargs == {'b': 4, 'c': 6}


def test_construct_arguments_does_not_overwrite_args_and_kwargs():
    s = Signature(bariza)
    args, kwargs = s.construct_arguments([1, 2], {'c': 3},
                                         {'a': 6, 'b': 6, 'c': 6})
    assert args == [1, 2]
    assert kwargs == {'c': 3}


def test_construct_arguments_overwrites_defaults():
    s = Signature(complex_function_name)
    args, kwargs = s.construct_arguments([], {}, {'a': 11, 'b': 12, 'c': 7})
    assert args == []
    assert kwargs == {'a': 11, 'b': 12, 'c': 7}


def test_construct_arguments_raises_if_args_unfilled():
    s = Signature(bariza)
    missing = re.compile(".*missing.*")
    with pytest.raises(TypeError) as excinfo:
        s.construct_arguments([], {}, {})
    assert missing.match(excinfo.value.args[0])
    with pytest.raises(TypeError) as excinfo:
        s.construct_arguments([1, 2], {}, {})
    assert missing.match(excinfo.value.args[0])
    with pytest.raises(TypeError) as excinfo:
        s.construct_arguments([1], {'b': 3}, {})
    assert missing.match(excinfo.value.args[0])
    with pytest.raises(TypeError) as excinfo:
        s.construct_arguments([1], {'c': 5}, {})
    assert missing.match(excinfo.value.args[0])


def test_construct_arguments_does_not_raise_if_all_args_filled():
    s = Signature(bariza)
    s.construct_arguments([1, 2, 3], {}, {})
    s.construct_arguments([1, 2], {'c': 6}, {})
    s.construct_arguments([1], {'b': 6, 'c': 6}, {})
    s.construct_arguments([], {'a': 6, 'b': 6, 'c': 6}, {})


def test_construct_arguments_does_not_raise_for_missing_defaults():
    s = Signature(complex_function_name)
    s.construct_arguments([], {}, {})


def test_construct_arguments_for_bound_method():
    s = Signature(SomeClass.bla)
    args, kwargs = s.construct_arguments([1], {'b': 2}, {'c': 3}, bound=True)
    assert args == [1]
    assert kwargs == {'b': 2, 'c': 3}


@pytest.mark.parametrize('func,expected', [
    (foo, "foo()"),
    (bariza, "bariza(a, b, c)"),
    (FunCTIonWithCAPItals, "FunCTIonWithCAPItals(a, b, c=3, **kwargs)"),
    (_name_with_underscore_, "_name_with_underscore_(fo, bar, *baz)"),
    (__double_underscore__, "__double_underscore__(man, o, *men, **oo)"),
    (old_name, "old_name(verylongvariablename)"),
    (renamed, "old_name(verylongvariablename)"),
    (generic, "generic(*args, **kwargs)"),
    (onlykwrgs, "onlykwrgs(**kwargs)")
])
def test_unicode_(func, expected):
    assert Signature(func).__unicode__() == expected


def test_unicode_special():
    assert re.match("complex_function_name\(a=1, b=u?'fo', c=9\)",
                    Signature(complex_function_name).__unicode__())


@pytest.mark.parametrize('name,func', zip(names, functions))
def test_repr_(name, func):
    regex = "<Signature at 0x[0-9a-fA-F]+ for '%s'>"
    assert re.match(regex % name, Signature(func).__repr__())
