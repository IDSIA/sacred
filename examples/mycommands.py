#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from sacred import Experiment

ex = Experiment('mycommands')


@ex.config
def cfg():
    name = 'John'


@ex.command
def greet(name):
    """
    Print a nice greet message.

    Uses the name from config.
    """
    print('Hello %s! Nice to greet you!' % name)


@ex.command
def shout():
    """
    Shout slang question for "what is up?"
    """
    print('WHAZZZUUUUUUUUUUP!!!????')


@ex.automain
def main():
    pass