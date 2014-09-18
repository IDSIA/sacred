#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
import pprint
import pydoc

from sacred.utils import iterate_separately, join_paths


BLUE = '\033[94m'
GREEN = '\033[92m'
RED = '\033[91m'
ENDC = '\033[0m'


def _my_safe_repr(objekt, context, maxlevels, level):
    """
    Used to override the pprint format method in order to get rid of unnecessary
    unicode prefixes. E.g.: 'John' instead of u'John'.
    """
    typ = pprint._type(objekt)
    if typ is unicode:
        try:
            objekt = str(objekt)
        except UnicodeEncodeError:
            pass
    return pprint._safe_repr(objekt, context, maxlevels, level)


def _cfgprint(x, key, added, updated, typechanges, indent=''):
    def colored(text):
        if key in added:
            return GREEN + text + ENDC
        elif key in typechanges:
            return RED + text + ENDC
        elif key in updated:
            return BLUE + text + ENDC
        else:
            return text

    last_key = key.split('.')[-1]
    if isinstance(x, dict):
        if last_key:
            print(colored('{}{}:'.format(indent, last_key)))
        for k, v in iterate_separately(x):
            subkey = join_paths(key, k)
            _cfgprint(v, subkey, added, updated, typechanges, indent + '  ')
    else:
        printer = pprint.PrettyPrinter(indent=len(indent)+2)
        printer.format = _my_safe_repr
        print(colored('{}{} = {}'.format(indent, last_key,
                                         printer.pformat(x))))

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
    added, updated, typechanges = _run.config_modifications
    print('Configuration', LEGEND + ':')
    _cfgprint(final_config, '', added, updated, typechanges)


def help_for_command(command):
    return pydoc.text.document(command)