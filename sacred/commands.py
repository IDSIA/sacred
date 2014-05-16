#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from pprint import pprint


def get_commands():
    return __commands__


def print_config(**config):
    """
    Print the configuration and exit.
    """
    for k in sorted(config.keys()):
        print("%s = " % k, end='')
        pprint(config[k], indent=2)



__commands__ = [print_config]