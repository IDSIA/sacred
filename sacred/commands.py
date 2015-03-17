#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import pprint
import pydoc
import re
from collections import namedtuple

from sacred.utils import PATHCHANGE, iterate_flattened_separately

__sacred__ = True  # marks files that should be filtered from stack traces

BLUE = '\033[94m'
GREEN = '\033[92m'
RED = '\033[91m'
ENDC = '\033[0m'


def non_unicode_repr(objekt, context, maxlevels, level):
    """
    Used to override the pprint format method to get rid of unicode prefixes.

    E.g.: 'John' instead of u'John'.
    """
    repr_string, isreadable, isrecursive = pprint._safe_repr(objekt, context,
                                                             maxlevels, level)
    if repr_string.startswith('u"') or repr_string.startswith("u'"):
        repr_string = repr_string[1:]
    return repr_string, isreadable, isrecursive

PRINTER = pprint.PrettyPrinter()
PRINTER.format = non_unicode_repr

ConfigEntry = namedtuple('ConfigEntry', 'key value added modified typechanged')
PathEntry = namedtuple('PathEntry', 'key added modified typechanged')


def iterate_marked(cfg, config_mods):
    for path, value in iterate_flattened_separately(cfg):
        if value is PATHCHANGE:
            yield path, PathEntry(
                key=path.rpartition('.')[2],
                added=path in config_mods.added,
                modified=path in config_mods.modified,
                typechanged=config_mods.typechanged.get(path))
        else:
            yield path, ConfigEntry(
                key=path.rpartition('.')[2],
                value=value,
                added=path in config_mods.added,
                modified=path in config_mods.modified,
                typechanged=config_mods.typechanged.get(path))


def format_entry(entry):
    color = ""
    if entry.typechanged:
        color = RED
    elif entry.added:
        color = GREEN
    elif entry.modified:
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
      green:  value modified
      blue:   value added
      red:    value modified but type changed
    """
    final_config = _run.config
    config_mods = _run.config_modifications
    print(format_config(final_config, config_mods))


def help_for_command(command):
    help_text = pydoc.text.document(command)
    # remove backspaces
    return re.subn('.\\x08', '', help_text)[0]


def print_dependencies(_run):
    """Print the detected source-files and dependencies."""
    print('Sources:')
    for source, digest in _run.experiment_info['sources']:
        print('  {:<43}  {}'.format(source, digest))

    print('\nDependencies:')
    for pack, version in _run.experiment_info['dependencies']:
        print('  {:<20} >= {}'.format(pack, version))
