#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
import pprint
import pydoc
from blessings import Terminal

term = Terminal()


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


def _iterate_separately(val):
    single_line_keys = [k for k in val.keys() if not isinstance(val[k], dict)]
    for k in sorted(single_line_keys):
        yield k, val[k]

    multi_line_keys = [k for k in val.keys() if isinstance(val[k], dict)]
    for k in sorted(multi_line_keys):
        yield k, val[k]


def _cfgprint(x, key, added, updated, typechanges, indent=''):
    def colored(text):
        if key in added:
            return term.blue(text)
        elif key in typechanges:
            return term.red(text)
        elif key in updated:
            return term.green(text)
        else:
            return text

    last_key = key.split('.')[-1]
    if isinstance(x, dict):
        if last_key:
            print(colored('{}{}:'.format(indent, last_key)))
        for k, v in _iterate_separately(x):
            subkey = (key + '.' + k).strip('.')
            _cfgprint(v, subkey, added, updated, typechanges, indent + '  ')
    else:
        printer = pprint.PrettyPrinter(indent=len(indent)+2)
        printer.format = _my_safe_repr
        print(colored('{}{} = {}'.format(indent, last_key,
                                         printer.pformat(x))))


def _flatten_keys(d):
    if isinstance(d, dict):
        for key in d:
            yield key
            for k in _flatten_keys(d[key]):
                yield key + '.' + k


def print_config(run):
    """
    Print the updated configuration and exit.

    Text is highlighted:
      green:  value updated
      blue:   value added
      red:    value updated but type changed
    """
    final_config = run.modrunner.config
    added, updated, typechanges = run.modrunner.get_config_modifications()
    print('Final Configuration:')
    _cfgprint(final_config, '', added, updated, typechanges)


def help_for_command(command):
    return pydoc.text.document(command)