#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function

import re

import pytest
from sacred.config.signature import Signature


# #############  function definitions to test on ##############################
def foo() -> None:
    return


def bariza(a: int, b: float, c: str):
    return a, b, c


def complex_function_name(a: int = 5, b: str = 'fo', c: float = 9):
    return a, b, c


def kwonly_args(a, *, b, c=10):
    return b


functions = [foo, bariza, complex_function_name, kwonly_args]

ids = ['foo', 'bariza', 'complex_function_name', 'kwonly_args']

names = ['foo', 'bariza', 'complex_function_name', 'kwonly_args']

arguments = [[], ['a', 'b', 'c'], ['a', 'b', 'c'], ['a', 'b', 'c']]

vararg_names = [None, None, None, None]

kw_wc_names = [None, None, None, None]

pos_arguments = [[], ['a', 'b', 'c'], [], ['a']]

kwarg_list = [{}, {}, {'a': 5, 'b': 'fo', 'c': 9}, {'c': 10}]


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


@pytest.mark.parametrize('function',
                         [foo, bariza, complex_function_name])
def test_construct_arguments_with_unexpected_kwargs_raises_typeerror(function):
    kwargs = {'zimbabwe': 23}
    unexpected = re.compile(".*unexpected.*zimbabwe.*")
    with pytest.raises(TypeError) as excinfo:
        Signature(function).construct_arguments([], kwargs, {})
    assert unexpected.match(excinfo.value.args[0])


@pytest.mark.parametrize('func,args', [
    (foo, [1]),
    (bariza, [1, 2, 3, 4]),
    (complex_function_name, [1, 2, 3, 4])
])
def test_construct_arguments_with_unexpected_args_raises_typeerror(func, args):
    unexpected = re.compile(".*unexpected.*")
    with pytest.raises(TypeError) as excinfo:
        Signature(func).construct_arguments(args, {}, {})
    assert unexpected.match(excinfo.value.args[0])


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


def test_construct_arguments_without_duplicates_passes():
    s = Signature(bariza)
    s.construct_arguments([1, 2], {'c': 5}, {})

    s = Signature(complex_function_name)
    s.construct_arguments([1], {'b': 4}, {})


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


def test_construct_arguments_completes_kwargs_from_options():
    s = Signature(bariza)
    args, kwargs = s.construct_arguments([2, 4], {}, {'c': 6})
    assert args == [2, 4]
    assert kwargs == {'c': 6}
    s = Signature(complex_function_name)
    args, kwargs = s.construct_arguments([], {'c': 6, 'b': 7}, {'a': 1})
    assert args == []
    assert kwargs == {'a': 1, 'c': 6, 'b': 7}


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
])
def test_unicode_(func, expected):
    assert Signature(func).__unicode__() == expected


@pytest.mark.parametrize('name,func', zip(names, functions))
def test_repr_(name, func):
    regex = "<Signature at 0x[0-9a-fA-F]+ for '%s'>"
    assert re.match(regex % name, Signature(func).__repr__())
