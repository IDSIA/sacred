#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from collections import namedtuple
import pprint
import pydoc
import re

from sacred.utils import iterate_flattened_separately, PATHCHANGE


BLUE = '\033[94m'
GREEN = '\033[92m'
RED = '\033[91m'
ENDC = '\033[0m'


def non_unicode_repr(objekt, context, maxlevels, level):
    """
    Used to override the pprint format method in order to get rid of
    unnecessary unicode prefixes. E.g.: 'John' instead of u'John'.
    """
    repr_string, isreadable, isrecursive = pprint._safe_repr(objekt, context,
                                                             maxlevels, level)
    if repr_string.startswith('u"') or repr_string.startswith("u'"):
        repr_string = repr_string[1:]
    return repr_string, isreadable, isrecursive

PRINTER = pprint.PrettyPrinter()
PRINTER.format = non_unicode_repr

ConfigEntry = namedtuple('ConfigEntry', 'key value added updated typechange')
PathEntry = namedtuple('PathEntry', 'key added updated typechange')


def iterate_marked(cfg, config_mods):
    for path, value in iterate_flattened_separately(cfg):
        if value is PATHCHANGE:
            yield path, PathEntry(
                key=path.rpartition('.')[2],
                added=path in config_mods.added,
                updated=path in config_mods.updated,
                typechange=config_mods.typechanges.get(path))
        else:
            yield path, ConfigEntry(
                key=path.rpartition('.')[2],
                value=value,
                added=path in config_mods.added,
                updated=path in config_mods.updated,
                typechange=config_mods.typechanges.get(path))


def format_entry(entry):
    color = ""
    if entry.typechange:
        color = RED
    elif entry.added:
        color = GREEN
    elif entry.updated:
        color = BLUE
    end = ENDC if color else ""
    if isinstance(entry, ConfigEntry):
        return color + entry.key + " = " + PRINTER.pformat(entry.value) + end
    else:  # isinstance(entry, PathEntry):
        return color + entry.key + ":" + end


def format_config(cfg, config_mods):
    lines = ['Configuration ' + LEGEND + ':']
    for path, entry in iterate_marked(cfg, config_mods):
        indent = '  ' + '  ' * path.count('.')
        lines.append(indent + format_entry(entry))
    return "\n".join(lines)

LEGEND = '(' + BLUE + 'modified' + ENDC +\
    ', ' + GREEN + 'added' + ENDC +\
    ', ' + RED + 'typechanged' + ENDC + ')'


def print_config(_run):
    """
    Print the updated configuration and exit.

    Text is highlighted:
      green:  value updated
      blue:   value added
      red:    value updated but type changed
    """
    final_config = _run.config
    config_mods = _run.config_modifications
    print(format_config(final_config, config_mods))


def help_for_command(command):
    help_text = pydoc.text.document(command)
    # remove backspaces
    return re.subn('.\\x08', '', help_text)[0]
