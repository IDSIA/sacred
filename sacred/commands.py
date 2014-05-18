#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from blessings import Terminal


def cfgprint(x, key, added, updated, typechanges, indent=''):
    term = Terminal()

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
        for k, v in x.items():
            if last_key:
                print(colored('{}{}:'.format(indent, last_key)))
            cfgprint(v, (key + '.' + k).strip('.'), added, updated, typechanges, indent + '  ')
    else:
        print(colored('{}{} = {}'.format(indent, last_key, x)))


def flatten_keys(d):
    if isinstance(d, dict):
        for key in d:
            yield key
            for k in flatten_keys(d[key]):
                yield key + '.' + k


def print_config(configs, final_cfg, updates):
    """
    Print the configuration and exit.
    """
    added = set()
    typechanges = {}
    updated = flatten_keys(updates)
    print('Final Configuration:')
    for config in configs:
        added |= config.added_values
        typechanges.update(config.typechanges)

    cfgprint(final_cfg, '', added, updated, typechanges)
