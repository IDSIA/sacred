#!/usr/bin/env python
# coding=utf-8
"""Defines the stock-commands that every sacred experiment ships with."""
from __future__ import division, print_function, unicode_literals

import pprint
import pydoc
import re
from collections import namedtuple

from sacred.config import save_config_file
from sacred.serializer import flatten
from sacred.utils import PATHCHANGE, iterate_flattened_separately

__sacred__ = True  # marks files that should be filtered from stack traces

__all__ = ('print_config', 'print_dependencies', 'save_config',
           'help_for_command')

BLUE = '\033[94m'
GREEN = '\033[92m'
RED = '\033[91m'
GREY = '\033[90m'
ENDC = '\033[0m'

LEGEND = '(' + BLUE + 'modified' + ENDC +\
    ', ' + GREEN + 'added' + ENDC +\
    ', ' + RED + 'typechanged' + ENDC +\
    ', ' + GREY + 'doc' + ENDC + ')'

ConfigEntry = namedtuple('ConfigEntry',
                         'key value added modified typechanged doc')
PathEntry = namedtuple('PathEntry', 'key added modified typechanged doc')


def _non_unicode_repr(objekt, context, maxlevels, level):
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
PRINTER.format = _non_unicode_repr


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
    print(_format_config(final_config, config_mods))


def help_for_command(command):
    """Get the help text (signature + docstring) for a command (function)."""
    help_text = pydoc.text.document(command)
    # remove backspaces
    return re.subn('.\\x08', '', help_text)[0]


def print_dependencies(_run):
    """Print the detected source-files and dependencies."""
    print('Dependencies:')
    for dep in _run.experiment_info['dependencies']:
        pack, _, version = dep.partition('==')
        print('  {:<20} == {}'.format(pack, version))

    print('\nSources:')
    for source, digest in _run.experiment_info['sources']:
        print('  {:<43}  {}'.format(source, digest))

    if _run.experiment_info['repositories']:
        repos = _run.experiment_info['repositories']
        print('\nVersion Control:')
        for repo in repos:
            mod = RED + 'M' if repo['dirty'] else ' '
            print('{} {:<43}  {}'.format(mod, repo['url'], repo['commit']) +
                  ENDC)
    print('')


def save_config(_config, _log, config_filename='config.json'):
    """
    Store the updated configuration in a file.

    By default uses the filename "config.json", but that can be changed by
    setting the config_filename config entry.
    """
    if 'config_filename' in _config:
        del _config['config_filename']
    _log.info('Saving config to "{}"'.format(config_filename))
    save_config_file(flatten(_config), config_filename)


def _iterate_marked(cfg, config_mods):
    for path, value in iterate_flattened_separately(cfg, ['__doc__']):
        if value is PATHCHANGE:
            yield path, PathEntry(
                key=path.rpartition('.')[2],
                added=path in config_mods.added,
                modified=path in config_mods.modified,
                typechanged=config_mods.typechanged.get(path),
                doc=config_mods.docs.get(path))
        else:
            yield path, ConfigEntry(
                key=path.rpartition('.')[2],
                value=value,
                added=path in config_mods.added,
                modified=path in config_mods.modified,
                typechanged=config_mods.typechanged.get(path),
                doc=config_mods.docs.get(path))


def _format_entry(indent, entry):
    color = ""
    indent = ' ' * indent
    if entry.typechanged:
        color = RED
    elif entry.added:
        color = GREEN
    elif entry.modified:
        color = BLUE
    if entry.key == '__doc__':
        color = GREY
        doc_string = entry.value.replace('\n', '\n' + indent)
        assign = '{}"""{}"""'.format(indent, doc_string)
    elif isinstance(entry, ConfigEntry):
        assign = indent + entry.key + " = " + PRINTER.pformat(entry.value)
    else:  # isinstance(entry, PathEntry):
        assign = indent + entry.key + ":"
    if entry.doc:
        doc_string = GREY + '# ' + entry.doc + ENDC
        if len(assign) <= 35:
            assign = "{:<35}  {}".format(assign, doc_string)
        else:
            assign += '    ' + doc_string
    end = ENDC if color else ""
    return color + assign + end


def _format_config(cfg, config_mods):
    lines = ['Configuration ' + LEGEND + ':']
    for path, entry in _iterate_marked(cfg, config_mods):
        indent = 2 + 2 * path.count('.')
        lines.append(_format_entry(indent, entry))
    return "\n".join(lines)
