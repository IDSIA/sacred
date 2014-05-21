#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
import pprint
import pydoc
from blessings import Terminal
from sacred.captured_function import CapturedFunction

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
        for k, v in x.items():
            _cfgprint(v, (key + '.' + k).strip('.'), added, updated, typechanges, indent + '  ')
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


def print_config(final_config, added, updated, typechanges):
    """
    Print the updated configuration and exit.

    Text is highlighted:
      green:  value updated
      blue:   value added
      red:    value updated but type changed
    """
    print('Final Configuration:')
    _cfgprint(final_config, '', added, updated, typechanges)


def help_for_command(command):
    if isinstance(command, CapturedFunction):
        return pydoc.text.document(command._wrapped_function)
    else:
        return pydoc.text.document(command)