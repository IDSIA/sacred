#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals


class CommandLineOption(object):
    short = None
    long = None
    description = None
    arg = None
    arg_description = None

    @classmethod
    def execute(cls, args, experiment):
        pass


def get_inheritors(cls):
    """Get a set of all classes that inherit from the given class."""
    subclasses = set()
    work = [cls]
    while work:
        parent = work.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                work.append(child)
    return subclasses


def gather_command_line_options():
    return sorted(get_inheritors(CommandLineOption), key=lambda x: x.__name__)


class HelpOption(CommandLineOption):
    short = 'h'
    long = 'help'
    description = 'Print this help message and exit.'


class DebugOption(CommandLineOption):
    short = 'd'
    long = 'debug'
    description = "Don't filter the stacktrace and automatically enter " \
                  "post-mortem debugging with pdb."

    @classmethod
    def execute(cls, args, experiment):
        experiment.debug = args


class LoglevelOption(CommandLineOption):
    short = 'l'
    long = 'loglevel'
    description = 'Adjust the loglevel.'
    arg = 'LEVEL'
    arg_description = 'Loglevel either as 0 - 50 or as string: DEBUG(10), ' \
                      'INFO(20), WARNING(30), ERROR(40), CRITICAL(50)'

    @classmethod
    def execute(cls, args, experiment):
        experiment.loglevel = args
