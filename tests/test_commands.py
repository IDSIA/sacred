#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
import pprint
import pytest
from sacred.commands import (iterate_marked, non_unicode_repr, ConfigEntry,
                             PathEntry, format_entry, BLUE, GREEN, RED, ENDC)


def test_non_unicode_repr():
    p = pprint.PrettyPrinter()
    p.format = non_unicode_repr
    # make sure there is no u' in the representation
    assert p.pformat(u'HelloWorld') == "'HelloWorld'"


@pytest.fixture
def cfg():
    return {
        'a': 0,
        'b': {},  # 1
        'c': {    # 2
            'cA': 3,
            'cB': 4,
            'cC': {  # 5
                'cC1': 6
            }
        },
        'd': {  # 7
            'dA': 8
        }
    }


def test_iterate_marked(cfg):
    assert list(iterate_marked(cfg, set(), set(), dict())) == \
        [('a', ConfigEntry('a', 0, False, False, None)),
         ('b', ConfigEntry('b', {}, False, False, None)),
         ('c', PathEntry('c', False, False, None)),
         ('c.cA', ConfigEntry('cA', 3, False, False, None)),
         ('c.cB', ConfigEntry('cB', 4, False, False, None)),
         ('c.cC', PathEntry('c.cC', False, False, None)),
         ('c.cC.cC1', ConfigEntry('cC1', 6, False, False, None)),
         ('d', PathEntry('d', False, False, None)),
         ('d.dA', ConfigEntry('dA', 8, False, False, None))
         ]


def test_iterate_marked_added(cfg):
    added = {'a', 'c.cB', 'c.cC.cC1'}
    assert list(iterate_marked(cfg, added, set(), dict())) == \
        [('a', ConfigEntry('a', 0, True, False, None)),
         ('b', ConfigEntry('b', {}, False, False, None)),
         ('c', PathEntry('c', False, False, None)),
         ('c.cA', ConfigEntry('cA', 3, False, False, None)),
         ('c.cB', ConfigEntry('cB', 4, True, False, None)),
         ('c.cC', PathEntry('c.cC', False, False, None)),
         ('c.cC.cC1', ConfigEntry('cC1', 6, True, False, None)),
         ('d', PathEntry('d', False, False, None)),
         ('d.dA', ConfigEntry('dA', 8, False, False, None))
         ]


def test_iterate_marked_updated(cfg):
    updated = {'b', 'c', 'c.cC.cC1'}
    assert list(iterate_marked(cfg, set(), updated, dict())) == \
        [('a', ConfigEntry('a', 0, False, False, None)),
         ('b', ConfigEntry('b', {}, False, True, None)),
         ('c', PathEntry('c', False, True, None)),
         ('c.cA', ConfigEntry('cA', 3, False, False, None)),
         ('c.cB', ConfigEntry('cB', 4, False, False, None)),
         ('c.cC', PathEntry('c.cC', False, False, None)),
         ('c.cC.cC1', ConfigEntry('cC1', 6, False, True, None)),
         ('d', PathEntry('d', False, False, None)),
         ('d.dA', ConfigEntry('dA', 8, False, False, None))
         ]


def test_iterate_marked_typechanged(cfg):
    typechanges = {'a': (bool, int),
                   'd.dA': (float, int)}
    assert list(iterate_marked(cfg, set(), set(), typechanges)) == \
        [('a', ConfigEntry('a', 0, False, False, (bool, int))),
         ('b', ConfigEntry('b', {}, False, False, None)),
         ('c', PathEntry('c', False, False, None)),
         ('c.cA', ConfigEntry('cA', 3, False, False, None)),
         ('c.cB', ConfigEntry('cB', 4, False, False, None)),
         ('c.cC', PathEntry('c.cC', False, False, None)),
         ('c.cC.cC1', ConfigEntry('cC1', 6, False, False, None)),
         ('d', PathEntry('d', False, False, None)),
         ('d.dA', ConfigEntry('dA', 8, False, False, (float, int)))
         ]


@pytest.mark.parametrize("entry,expected", [
    (ConfigEntry('a', 0, False, False, None),       "a = 0"),
    (ConfigEntry('foo', 'bar', False, False, None), "foo = 'bar'"),
    (ConfigEntry('b', [0, 1], False, False, None),  "b = [0, 1]"),
    (ConfigEntry('c', True, False, False, None),    "c = True"),
    (ConfigEntry('d', 0.5, False, False, None),     "d = 0.5"),
    (ConfigEntry('e', {}, False, False, None),      "e = {}"),
    # Path entries
    (PathEntry('f', False, False, None),     "f:"),
    (PathEntry('f.g', False, False, None),   "f.g:"),
    (PathEntry('f.g.h', False, False, None), "f.g.h:"),
])
def test_format_entry(entry, expected):
    assert format_entry(entry) == expected


@pytest.mark.parametrize("entry,color", [
    (ConfigEntry('a', 1, True, False, None),         GREEN),
    (ConfigEntry('b', 2, False, True, None),         BLUE),
    (ConfigEntry('c', 3, False, False, (bool, int)), RED),
    (ConfigEntry('d', 4, True, True, None),          GREEN),
    (ConfigEntry('e', 5, True, False, (bool, int)),  RED),
    (ConfigEntry('f', 6, False, True, (bool, int)),  RED),
    (ConfigEntry('g', 7, True, True, (bool, int)),   RED),
    # Path entries
    (PathEntry('a', True, False, None),         GREEN),
    (PathEntry('b', False, True, None),         BLUE),
    (PathEntry('c', False, False, (bool, int)), RED),
    (PathEntry('d', True, True, None),          GREEN),
    (PathEntry('e', True, False, (bool, int)),  RED),
    (PathEntry('f', False, True, (bool, int)),  RED),
    (PathEntry('g', True, True, (bool, int)),   RED),
])
def test_format_entry_colors(entry, color):
    s = format_entry(entry)
    assert s.startswith(color)
    assert s.endswith(ENDC)
