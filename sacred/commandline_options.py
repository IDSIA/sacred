#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from sacred.utils import get_inheritors


class CommandLineOption(object):

    """
    Base class for all command-line options.

    To implement a new command-line option just inherit from this class.
    Then add the `flag` class-attribute to specify the name and a class
    docstring with the description.
    If your command-line option should take an argument you must also provide
    its name via the `arg` class attribute and its description as
    `arg_description`.
    Finally you need to implement the `execute` classmethod. It receives the
    value of the argument (if applicable) and the current run. You can modify
    the run object in any way.
    """

    flag = None
    """ The full name of the command line option."""

    short_flag = None
    """ The (one-letter) short form (defaults to first letter of flag) """

    arg = None
    """ Name of the argument (optional) """

    arg_description = None
    """ Description of the argument (optional) """

    @classmethod
    def get_flag(cls):
        if cls.short_flag is None:
            assert cls.flag, "No flag specified for {}!\n".format(cls.__name__)
            return cls.flag[:1], cls.flag
        else:
            return cls.short_flag, cls.flag

    @classmethod
    def execute(cls, args, run):
        """
        Modify the current Run base on this command-line option.

        This function is executed after contstructing the Run object, but
        before actually starting it.
        :param args: If this command-line option accepts an argument this will
                     be value of that argument if set or None.
                     Otherwise it is either True or False.
        :type args: bool | str
        :param run: The current run to be modified
        :type run: sacred.run.Run
        """
        pass


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
        run.debug = bool(args)


class LoglevelOption(CommandLineOption):

    """Adjust the loglevel."""

    flag = 'loglevel'
    arg = 'LEVEL'
    arg_description = 'Loglevel either as 0 - 50 or as string: DEBUG(10), ' \
                      'INFO(20), WARNING(30), ERROR(40), CRITICAL(50)'

    @classmethod
    def execute(cls, args, run):
        if args is None:
            return
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
        if args is None:
            return
        run.comment = args
