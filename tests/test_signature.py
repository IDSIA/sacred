#!/usr/bin/python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import re
import pytest
from sacred.signature import Signature


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

def test_constructor_extract_function_name():
    names = ['foo', 'bariza', 'complex_function_name',
             'FunCTIonWithCAPItals', '_name_with_underscore_',
             '__double_underscore__', 'old_name', 'old_name']
    for f, name in zip(functions, names):
        s = Signature(f)
        print(f.__name__)
        assert s.name == name


def test_constructor_extracts_all_arguments():
    arguments = [[], ['a', 'b', 'c'], ['a', 'b', 'c'], ['a', 'b', 'c'],
                     ['fo', 'bar'], ['man', 'o'], ['verylongvariablename'],
                     ['verylongvariablename']]
    for f, args in zip(functions, arguments):
        s = Signature(f)
        print(f.__name__)
        assert s.arguments == args


def test_constructor_extract_vararg_name():
    vararg_names = [None, None, None, None, 'baz', 'men', None, None]
    for f, varg in zip(functions, vararg_names):
        s = Signature(f)
        print(f.__name__)
        assert s.vararg_name == varg


def test_constructor_extract_kwargs_wildcard_name():
    kw_wc_names = [None, None, None, 'kwargs', None, 'oo', None, None]
    for f, kw_wc in zip(functions, kw_wc_names):
        s = Signature(f)
        print(f.__name__)
        assert s.kw_wildcard_name == kw_wc


def test_constructor_extract_positional_arguments():
    pos_args = [[], ['a', 'b', 'c'], [], ['a', 'b'], ['fo', 'bar'],
                    ['man', 'o'], ['verylongvariablename']]
    for f, pargs in zip(functions, pos_args):
        s = Signature(f)
        print(f.__name__)
        assert s.positional_args == pargs


def test_constructor_extract_kwargs():
    kwarg_list = [{}, {}, {'a': 1, 'b': 'fo', 'c': 9}, {'c': 3}, {}, {}, {}]
    for f, kwargs in zip(functions, kwarg_list):
        s = Signature(f)
        print(f.__name__)
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


def test_construct_arguments_with_unexpected_kwargs_raises_typeerror():
    kwargs = {'zimbabwe': 23}
    unexpected = re.compile(".*unexpected.*zimbabwe.*")
    with pytest.raises(TypeError) as excinfo:
        Signature(foo).construct_arguments([], kwargs, {})
    assert unexpected.match(excinfo.value.args[0])

    with pytest.raises(TypeError) as excinfo:
        Signature(bariza).construct_arguments([], kwargs, {})
    assert unexpected.match(excinfo.value.args[0])

    with pytest.raises(TypeError) as excinfo:
        s = Signature(complex_function_name)
        s.construct_arguments([], kwargs, {})
    assert unexpected.match(excinfo.value.args[0])
    with pytest.raises(TypeError) as excinfo:
        s = Signature(_name_with_underscore_)
        s.construct_arguments([], kwargs, {})
    assert unexpected.match(excinfo.value.args[0])
    with pytest.raises(TypeError) as excinfo:
        Signature(old_name).construct_arguments([], kwargs, {})
    assert unexpected.match(excinfo.value.args[0])
    with pytest.raises(TypeError) as excinfo:
        Signature(renamed).construct_arguments([], kwargs, {})
    assert unexpected.match(excinfo.value.args[0])


def test_construct_arguments_with_unexpected_args_raises_typeerror():
    unexpected = re.compile(".*unexpected.*")
    with pytest.raises(TypeError) as excinfo:
        Signature(foo).construct_arguments([1], {}, {})
    assert unexpected.match(excinfo.value.args[0])
    with pytest.raises(TypeError) as excinfo:
        Signature(bariza).construct_arguments([1, 2, 3, 4], {}, {})
    assert unexpected.match(excinfo.value.args[0])
    with pytest.raises(TypeError) as excinfo:
        s = Signature(complex_function_name)
        s.construct_arguments([1, 2, 3, 4], {}, {})
    assert unexpected.match(excinfo.value.args[0])
    with pytest.raises(TypeError) as excinfo:
        Signature(old_name).construct_arguments([1, 2], {}, {})
    assert unexpected.match(excinfo.value.args[0])
    with pytest.raises(TypeError) as excinfo:
        Signature(renamed).construct_arguments([1, 2], {}, {})
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


def test_unicode_():
    assert Signature(foo).__unicode__() == "foo()"
    assert Signature(bariza).__unicode__() == "bariza(a, b, c)"
    assert re.match("complex_function_name\(a=1, b=u?'fo', c=9\)", Signature(complex_function_name).__unicode__())
    assert Signature(FunCTIonWithCAPItals).__unicode__() == "FunCTIonWithCAPItals(a, b, c=3, **kwargs)"
    assert Signature(_name_with_underscore_).__unicode__() == "_name_with_underscore_(fo, bar, *baz)"
    assert Signature(__double_underscore__).__unicode__() == "__double_underscore__(man, o, *men, **oo)"
    assert Signature(old_name).__unicode__() == "old_name(verylongvariablename)"
    assert Signature(renamed).__unicode__() == "old_name(verylongvariablename)"
    assert Signature(generic).__unicode__() == "generic(*args, **kwargs)"
    assert Signature(onlykwrgs).__unicode__() == "onlykwrgs(**kwargs)"


def test_repr_():
    regex = "<Signature at 0x[0-9a-fA-F]+ for '%s'>"
    assert re.match(regex % 'foo', Signature(foo).__repr__())
    assert re.match(regex % 'bariza', Signature(bariza).__repr__())
    assert re.match(regex % 'complex_function_name', Signature(complex_function_name).__repr__())
    assert re.match(regex % 'FunCTIonWithCAPItals', Signature(FunCTIonWithCAPItals).__repr__())
    assert re.match(regex % '_name_with_underscore_', Signature(_name_with_underscore_).__repr__())
    assert re.match(regex % '__double_underscore__', Signature(__double_underscore__).__repr__())
    assert re.match(regex % 'old_name', Signature(old_name).__repr__())
    assert re.match(regex % 'old_name', Signature(renamed).__repr__())
    assert re.match(regex % 'generic', Signature(generic).__repr__())
    assert re.match(regex % 'onlykwrgs', Signature(onlykwrgs).__repr__())
