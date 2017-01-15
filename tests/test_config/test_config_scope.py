#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import pytest
import sacred.optional as opt
from sacred.config.config_scope import (ConfigScope, dedent_function_body,
                                        dedent_line, get_function_body,
                                        is_empty_or_comment)
from sacred.config.custom_containers import DogmaticDict, DogmaticList


@pytest.fixture
def conf_scope():
    @ConfigScope
    def cfg():
        # description for a
        a = 1
        # description for b and c
        b, c = 2.0, True
        # d and dd are both strings
        d = dd = 'string'
        e = [1, 2, 3]  # inline description for e
        f = {'a': 'b', 'c': 'd'}
        composit1 = a + b
        # pylint: this comment is filtered out
        composit2 = f['c'] + "ada"

        func1 = lambda: 23

        deriv = func1()

        def func2(a):
            return 'Nothing to report' + a

        some_type = int

    cfg()
    return cfg


def test_result_of_config_scope_is_dict(conf_scope):
    cfg = conf_scope()
    assert isinstance(cfg, dict)


def test_result_of_config_scope_contains_keys(conf_scope):
    cfg = conf_scope()
    assert set(cfg.keys()) == {'a', 'b', 'c', 'd', 'dd', 'e', 'f',
                               'composit1', 'composit2', 'deriv', 'func1',
                               'func2', 'some_type'}

    assert cfg['a'] == 1
    assert cfg['b'] == 2.0
    assert cfg['c']
    assert cfg['d'] == 'string'
    assert cfg['dd'] == 'string'
    assert cfg['e'] == [1, 2, 3]
    assert cfg['f'] == {'a': 'b', 'c': 'd'}
    assert cfg['composit1'] == 3.0
    assert cfg['composit2'] == 'dada'
    assert cfg['func1']() == 23
    assert cfg['func2'](', sir!') == 'Nothing to report, sir!'
    assert cfg['some_type'] == int
    assert cfg['deriv'] == 23


def test_fixing_values(conf_scope):
    cfg = conf_scope({'a': 100})
    assert cfg['a'] == 100
    assert cfg['composit1'] == 102.0


def test_fixing_nested_dicts(conf_scope):
    cfg = conf_scope({'f': {'c': 't'}})
    assert cfg['f']['a'] == 'b'
    assert cfg['f']['c'] == 't'
    assert cfg['composit2'] == 'tada'


def test_adding_values(conf_scope):
    cfg = conf_scope({'g': 23, 'h': {'i': 10}})
    assert cfg['g'] == 23
    assert cfg['h'] == {'i': 10}
    assert cfg.added == {'g', 'h', 'h.i'}


def test_typechange(conf_scope):
    cfg = conf_scope({'a': 'bar', 'b': 'foo', 'c': 1})
    assert cfg.typechanged == {'a': (int, type('bar')),
                               'b': (float, type('foo')),
                               'c': (bool, int)}


def test_nested_typechange(conf_scope):
    cfg = conf_scope({'f': {'a': 10}})
    assert cfg.typechanged == {'f.a': (type('a'), int)}


def test_config_docs(conf_scope):
    cfg = conf_scope()
    assert cfg.docs == {
        'a': 'description for a',
        'b': 'description for b and c',
        'c': 'description for b and c',
        'd': 'd and dd are both strings',
        'dd': 'd and dd are both strings',
        'e': 'inline description for e',
        'seed': 'the random seed for this experiment'
    }


def is_dogmatic(a):
    if isinstance(a, (DogmaticDict, DogmaticList)):
        return True
    elif isinstance(a, dict):
        return any(is_dogmatic(v) for v in a.values())
    elif isinstance(a, (list, tuple)):
        return any(is_dogmatic(v) for v in a)


def test_conf_scope_is_not_dogmatic(conf_scope):
    assert not is_dogmatic(conf_scope({'e': [1, 1, 1]}))


@pytest.mark.skipif(not opt.has_numpy, reason="requires numpy")
def test_conf_scope_handles_numpy_bools():
    @ConfigScope
    def conf_scope():
        a = opt.np.bool_(1)

    cfg = conf_scope()
    assert 'a' in cfg
    assert cfg['a']


def test_conf_scope_can_access_preset():
    @ConfigScope
    def conf_scope(a):
        answer = 2 * a

    cfg = conf_scope(preset={'a': 21})
    assert cfg['answer'] == 42


def test_conf_scope_contains_presets():
    @ConfigScope
    def conf_scope(a):
        answer = 2 * a

    cfg = conf_scope(preset={'a': 21, 'unrelated': True})
    assert set(cfg.keys()) == {'a', 'answer', 'unrelated'}
    assert cfg['a'] == 21
    assert cfg['answer'] == 42
    assert cfg['unrelated'] is True


def test_conf_scope_cannot_access_undeclared_presets():
    @ConfigScope
    def conf_scope():
        answer = 2 * a

    with pytest.raises(NameError):
        conf_scope(preset={'a': 21})


def test_conf_scope_can_access_fallback():
    @ConfigScope
    def conf_scope(a):
        answer = 2 * a

    cfg = conf_scope(fallback={'a': 21})
    assert cfg['answer'] == 42


def test_conf_scope_does_not_contain_fallback():
    @ConfigScope
    def conf_scope(a):
        answer = 2 * a

    cfg = conf_scope(fallback={'a': 21, 'b': 10})
    assert set(cfg.keys()) == {'answer'}


def test_conf_scope_cannot_access_undeclared_fallback():
    @ConfigScope
    def conf_scope():
        answer = 2 * a

    with pytest.raises(NameError):
        conf_scope(fallback={'a': 21})


def test_conf_scope_can_access_fallback_and_preset():
    @ConfigScope
    def conf_scope(a, b):
        answer = a + b

    cfg = conf_scope(preset={'b': 40}, fallback={'a': 2})
    assert cfg['answer'] == 42


def test_conf_raises_for_unaccessible_arguments():
    @ConfigScope
    def conf_scope(a, b, c):
        answer = 42

    with pytest.raises(KeyError):
        conf_scope(preset={'a': 1}, fallback={'b': 2})


def test_can_access_globals_from_original_scope():
    from .enclosed_config_scope import cfg as conf_scope
    cfg = conf_scope()
    assert set(cfg.keys()) == {'answer'}
    assert cfg['answer'] == 42


SEVEN = 7


def test_cannot_access_globals_from_calling_scope():
    from .enclosed_config_scope import cfg2 as conf_scope
    with pytest.raises(NameError):
        conf_scope()  # would require SEVEN


def test_fixed_subentry_of_preset():
    @ConfigScope
    def conf_scope():
        pass

    cfg = conf_scope(preset={'d': {'a': 1, 'b': 2}}, fixed={'d': {'a': 10}})

    assert set(cfg.keys()) == {'d'}
    assert set(cfg['d'].keys()) == {'a', 'b'}
    assert cfg['d']['a'] == 10
    assert cfg['d']['b'] == 2


@pytest.mark.parametrize("line,indent,expected", [
    ('    a=5', '    ', 'a=5'),
    ('  a=5',   '    ', 'a=5'),
    ('a=5',     '    ', 'a=5'),
    ('    a=5', '  ',   '  a=5'),
    ('    a=5', '',     '    a=5'),
    ('    a=5', '\t',   '    a=5'),
    ('  a=5', '      ', 'a=5'),
    ('    a=5', '  \t', '  a=5')
])
def test_dedent_line(line, indent, expected):
    assert dedent_line(line, indent) == expected


@pytest.mark.parametrize("line,expected", [
    ('', True),
    ('  ', True),
    ('\n', True),
    ('    \n', True),
    ('  \t \n', True),
    ('#comment', True),
    ('   #comment', True),
    ('  a=5 # not comment', False),
    ('a=5', False),
    ('"""', False),
    ("'''", False)

])
def test_is_empty_or_comment(line, expected):
    assert is_empty_or_comment(line) == expected


def evil_indentation_func(a,
                                    b,
c, d):
# Lets do the most evil things with indentation
  # 1
    # 2
     # ran
        """ and also in the docstring
             atrne
    uiaeue
utdr
    """
        alpha = 0.1
        d = ('even', 'more',
    'evilness')
        wat = """ multi
    line
strings
    """
# another comment
        # this one is ok
    # madness
        foo=12

        def subfunc():
            return 23

body = '''# Lets do the most evil things with indentation
  # 1
    # 2
     # ran
        """ and also in the docstring
             atrne
    uiaeue
utdr
    """
        alpha = 0.1
        d = ('even', 'more',
    'evilness')
        wat = """ multi
    line
strings
    """
# another comment
        # this one is ok
    # madness
        foo=12

        def subfunc():
            return 23
'''

dedented_body = '''# Lets do the most evil things with indentation
# 1
# 2
# ran
""" and also in the docstring
     atrne
uiaeue
utdr
"""
alpha = 0.1
d = ('even', 'more',
'evilness')
wat = """ multi
line
strings
"""
# another comment
# this one is ok
# madness
foo=12

def subfunc():
    return 23
'''


def test_dedent_body():
    assert dedent_function_body(body) == dedented_body


def test_get_function_body():
    func_body, line_offset = get_function_body(evil_indentation_func)
    assert func_body == body


def test_config_scope_can_deal_with_indentation_madness():
    # assert_no_raise:
    ConfigScope(evil_indentation_func)
