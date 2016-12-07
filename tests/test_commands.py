#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals

import pprint

import pytest
from sacred.commands import (BLUE, ENDC, GREY, GREEN, RED, ConfigEntry,
                             PathEntry, _format_config, _format_entry,
                             help_for_command, _iterate_marked, _non_unicode_repr)
from sacred.config.config_summary import ConfigSummary


def test_non_unicode_repr():
    p = pprint.PrettyPrinter()
    p.format = _non_unicode_repr
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
    assert list(_iterate_marked(cfg, ConfigSummary())) == \
        [('a', ConfigEntry('a', 0, False, False, None, None)),
         ('b', ConfigEntry('b', {}, False, False, None, None)),
         ('c', PathEntry('c', False, False, None, None)),
         ('c.cA', ConfigEntry('cA', 3, False, False, None, None)),
         ('c.cB', ConfigEntry('cB', 4, False, False, None, None)),
         ('c.cC', PathEntry('cC', False, False, None, None)),
         ('c.cC.cC1', ConfigEntry('cC1', 6, False, False, None, None)),
         ('d', PathEntry('d', False, False, None, None)),
         ('d.dA', ConfigEntry('dA', 8, False, False, None, None))
         ]


def test_iterate_marked_added(cfg):
    added = {'a', 'c.cB', 'c.cC.cC1'}
    assert list(_iterate_marked(cfg, ConfigSummary(added=added))) == \
        [('a', ConfigEntry('a', 0, True, False, None, None)),
         ('b', ConfigEntry('b', {}, False, False, None, None)),
         ('c', PathEntry('c', False, True, None, None)),
         ('c.cA', ConfigEntry('cA', 3, False, False, None, None)),
         ('c.cB', ConfigEntry('cB', 4, True, False, None, None)),
         ('c.cC', PathEntry('cC', False, True, None, None)),
         ('c.cC.cC1', ConfigEntry('cC1', 6, True, False, None, None)),
         ('d', PathEntry('d', False, False, None, None)),
         ('d.dA', ConfigEntry('dA', 8, False, False, None, None))
         ]


def test_iterate_marked_updated(cfg):
    modified = {'b', 'c', 'c.cC.cC1'}
    assert list(_iterate_marked(cfg, ConfigSummary(modified=modified))) == \
        [('a', ConfigEntry('a', 0, False, False, None, None)),
         ('b', ConfigEntry('b', {}, False, True, None, None)),
         ('c', PathEntry('c', False, True, None, None)),
         ('c.cA', ConfigEntry('cA', 3, False, False, None, None)),
         ('c.cB', ConfigEntry('cB', 4, False, False, None, None)),
         ('c.cC', PathEntry('cC', False, True, None, None)),
         ('c.cC.cC1', ConfigEntry('cC1', 6, False, True, None, None)),
         ('d', PathEntry('d', False, False, None, None)),
         ('d.dA', ConfigEntry('dA', 8, False, False, None, None))
         ]


def test_iterate_marked_typechanged(cfg):
    typechanged = {'a': (bool, int),
                   'd.dA': (float, int)}
    result = list(_iterate_marked(cfg, ConfigSummary(typechanged=typechanged)))
    assert result == \
        [('a', ConfigEntry('a', 0, False, False, (bool, int), None)),
         ('b', ConfigEntry('b', {}, False, False, None, None)),
         ('c', PathEntry('c', False, False, None, None)),
         ('c.cA', ConfigEntry('cA', 3, False, False, None, None)),
         ('c.cB', ConfigEntry('cB', 4, False, False, None, None)),
         ('c.cC', PathEntry('cC', False, False, None, None)),
         ('c.cC.cC1', ConfigEntry('cC1', 6, False, False, None, None)),
         ('d', PathEntry('d', False, True, None, None)),
         ('d.dA', ConfigEntry('dA', 8, False, False, (float, int), None))
         ]


@pytest.mark.parametrize("entry,expected", [
    (ConfigEntry('a', 0, False, False, None, None),       "a = 0"),
    (ConfigEntry('foo', 'bar', False, False, None, None), "foo = 'bar'"),
    (ConfigEntry('b', [0, 1], False, False, None, None),  "b = [0, 1]"),
    (ConfigEntry('c', True, False, False, None, None),    "c = True"),
    (ConfigEntry('d', 0.5, False, False, None, None),     "d = 0.5"),
    (ConfigEntry('e', {}, False, False, None, None),      "e = {}"),
    # Path entries
    (PathEntry('f', False, False, None, None), "f:"),
    # Docstring entry
    (ConfigEntry('__doc__', 'multiline\ndocstring', False, False, None, None),
     GREY + '"""multiline\ndocstring"""' + ENDC),
])
def test_format_entry(entry, expected):
    assert _format_entry(0, entry) == expected


@pytest.mark.parametrize("entry,color", [
    (ConfigEntry('a', 1, True, False, None, None),         GREEN),
    (ConfigEntry('b', 2, False, True, None, None),         BLUE),
    (ConfigEntry('c', 3, False, False, (bool, int), None), RED),
    (ConfigEntry('d', 4, True, True, None, None),          GREEN),
    (ConfigEntry('e', 5, True, False, (bool, int), None),  RED),
    (ConfigEntry('f', 6, False, True, (bool, int), None),  RED),
    (ConfigEntry('g', 7, True, True, (bool, int), None),   RED),
    # Path entries
    (PathEntry('a', True, False, None, None),         GREEN),
    (PathEntry('b', False, True, None, None),         BLUE),
    (PathEntry('c', False, False, (bool, int), None), RED),
    (PathEntry('d', True, True, None, None),          GREEN),
    (PathEntry('e', True, False, (bool, int), None),  RED),
    (PathEntry('f', False, True, (bool, int), None),  RED),
    (PathEntry('g', True, True, (bool, int), None),   RED),
])
def test_format_entry_colors(entry, color):
    s = _format_entry(0, entry)
    assert s.startswith(color)
    assert s.endswith(ENDC)


def test_format_config(cfg):
    cfg_text = _format_config(cfg, ConfigSummary())
    lines = cfg_text.split('\n')
    assert lines[0].startswith('Configuration')
    assert lines[1].find(' a = 0') > -1
    assert lines[2].find(' b = {}') > -1
    assert lines[3].find(' c:') > -1
    assert lines[4].find(' cA = 3') > -1
    assert lines[5].find(' cB = 4') > -1
    assert lines[6].find(' cC:') > -1
    assert lines[7].find(' cC1 = 6') > -1
    assert lines[8].find(' d:') > -1
    assert lines[9].find(' dA = 8') > -1


def test_help_for_command():
    def my_command():
        """This is my docstring"""
        pass

    help_text = help_for_command(my_command)
    assert help_text.find("my_command") > -1
    assert help_text.find("This is my docstring") > -1
