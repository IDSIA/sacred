#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals


class CommandLineOption(object):
    short_flag = None
    flag = None
    arg = None
    arg_description = None

    @classmethod
    def get_flag(cls):
        if cls.short_flag is None:
            assert cls.flag, "No flag specified for {}!\n".format(cls.__name__)
            return cls.flag[:1], cls.flag
        else:
            return cls.short_flag, cls.flag

    @classmethod
    def execute(cls, args, run):
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

    """Print this help message and exit."""

    flag = 'help'


class DebugOption(CommandLineOption):

    """
    Run in debug mode.

    Don't filter the stacktrace and automatically enter post-mortem debugging
    with pdb.
    """

    flag = 'debug'

    @classmethod
    def execute(cls, args, run):
        run.debug = args


class LoglevelOption(CommandLineOption):

    """Adjust the loglevel."""

    flag = 'loglevel'
    arg = 'LEVEL'
    arg_description = 'Loglevel either as 0 - 50 or as string: DEBUG(10), ' \
                      'INFO(20), WARNING(30), ERROR(40), CRITICAL(50)'

    @classmethod
    def execute(cls, args, run):
        try:
            lvl = int(args)
        except ValueError:
            lvl = args
        run.root_logger.setLevel(lvl)


class MessageOption(CommandLineOption):

    """Adds a message to the run."""

    flag = 'comment'
    arg = 'COMMENT'
    arg_description = 'A comment that should be stored along with the run.'

    @classmethod
    def execute(cls, args, run):
        run.comment = args
