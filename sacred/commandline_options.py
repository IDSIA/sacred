#!/usr/bin/env python
# coding=utf-8
"""
This module provides the basis for all command-line options (flags) in sacred.

It defines the base class CommandLineOption and the standard supported flags.
Some further options that add observers to the run are defined alongside those.
"""

import warnings

from sacred.commands import print_config
from sacred.settings import SETTINGS
from sacred.utils import convert_camel_case_to_snake_case, get_inheritors


class CommandLineOption:
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

    If the command line option depends on one or more installed packages, those
    should be imported in the `apply` method to get a proper ImportError
    if the packages are not available.
    """

    def __init__(self, enabled=True, short_flag=None,
                 arg=None, arg_description=None):
        """"
        short_flag
        The (one-letter) short form (defaults to first letter of flag)
        arg
        Name of the argument (optional)
        arg_description
        Description of the argument (optional)
        """
        self.enabled = enabled
        self.short_flag = short_flag
        self.arg = arg
        self.arg_description = arg_description

    def get_flag(self):
        # Get the flag name from the class name
        flag = self.__class__.__name__
        if flag.endswith("Option"):
            flag = flag[:-6]
        return '--' + convert_camel_case_to_snake_case(flag)

    def get_short_flag(self):
        if self.short_flag is None:
            return '-' + self.get_flag()[2]
        else:
            return '-' + self.short_flag

    def get_flags(self):
        """
        Return the short and the long version of this option.

        The long flag (e.g. '--foo_bar'; used on the command-line like this:
        --foo_bar[=ARGS]) is derived from the class-name by stripping away any
        -Option suffix and converting the rest to snake_case.

        The short flag (e.g. '-f'; used on the command-line like this:
        -f [ARGS]) the short_flag class-member if that is set, or the first
        letter of the long flag otherwise.

        Returns
        -------
        (str, str)
            tuple of short-flag, and long-flag

        """
        return self.get_short_flag(), self.get_flag()

    def apply(self, args, run):
        """
        Modify the current Run base on this command-line option.

        This function is executed after constructing the Run object, but
        before actually starting it.

        Parameters
        ----------
        args : bool | str
            If this command-line option accepts an argument this will be value
            of that argument if set or None.
            Otherwise it is either True or False.
        run :  sacred.run.Run
            The current run to be modified

        """
        pass


def gather_command_line_options(filter_disabled=None):
    """Get a sorted list of all CommandLineOption subclasses."""
    if filter_disabled is None:
        filter_disabled = not SETTINGS.COMMAND_LINE.SHOW_DISABLED_OPTIONS
    options = [opt() for opt in get_inheritors(CommandLineOption)
               if not filter_disabled or opt._enabled]
    return sorted(options, key=lambda opt: opt.__class__.__name__)


class HelpOption(CommandLineOption):
    """Print this help message and exit."""


class DebugOption(CommandLineOption):
    """
    Suppress warnings about missing observers and don't filter the stacktrace.

    Also enables usage with ipython --pdb.
    """

    def apply(self, args, run):
        """Set this run to debug mode."""
        run.debug = True


class PDBOption(CommandLineOption):
    """Automatically enter post-mortem debugging with pdb on failure."""

    def __init__(self):
        super().__init__(short_flag='D')

    def apply(self, args, run):
        run.pdb = True


class LoglevelOption(CommandLineOption):
    """Adjust the loglevel."""

    def __init__(self):
        super().__init__(
            arg='LEVEL',
            arg_description='Loglevel either as 0 - 50 or as string: '
                            'DEBUG(10), INFO(20), WARNING(30), '
                            'ERROR(40), CRITICAL(50)')

    def apply(self, args, run):
        """Adjust the loglevel of the root-logger of this run."""
        # TODO: sacred.initialize.create_run already takes care of this

        try:
            lvl = int(args)
        except ValueError:
            lvl = args
        run.root_logger.setLevel(lvl)


class CommentOption(CommandLineOption):
    """Adds a message to the run."""

    def __init__(self):
        super().__init__(arg='COMMENT',
                         arg_description='A comment that should be stored '
                                         'along with the run.')

    def apply(self, args, run):
        """Add a comment to this run."""
        run.meta_info['comment'] = args


class BeatIntervalOption(CommandLineOption):
    """Control the rate of heartbeat events."""

    def __init__(self):
        super().__init__(arg='BEAT_INTERVAL',
                         arg_description="Time between two heartbeat "
                                         "events measured in seconds.")

    def apply(self, args, run):
        """Set the heart-beat interval for this run."""
        run.beat_interval = float(args)


class UnobservedOption(CommandLineOption):
    """Ignore all observers for this run."""

    def apply(self, args, run):
        """Set this run to unobserved mode."""
        run.unobserved = True


class QueueOption(CommandLineOption):
    """Only queue this run, do not start it."""

    def apply(self, args, run):
        """Set this run to queue only mode."""
        run.queue_only = True


class ForceOption(CommandLineOption):
    """Disable warnings about suspicious changes for this run."""

    def apply(self, args, run):
        """Set this run to not warn about suspicous changes."""
        run.force = True


class PriorityOption(CommandLineOption):
    """Sets the priority for a queued up experiment."""

    def __init__(self):
        super().__init__(
            short_flag='P',
            arg='PRIORITY',
            arg_description='The (numeric) priority for this run.')

    def apply(self, args, run):
        """Add priority info for this run."""
        try:
            priority = float(args)
        except ValueError:
            raise ValueError("The PRIORITY argument must be a number! "
                             "(but was '{}')".format(args))
        run.meta_info['priority'] = priority


class EnforceCleanOption(CommandLineOption):
    """Fail if any version control repository is dirty."""

    def apply(self, args, run):
        try:
            import git  # NOQA
        except ImportError:
            warnings.warn('GitPython must be installed to use the '
                          '--enforce-clean option.')
            raise
        repos = run.experiment_info['repositories']
        if not repos:
            raise RuntimeError('No version control detected. '
                               'Cannot enforce clean repository.\n'
                               'Make sure that your sources under VCS and the '
                               'corresponding python package is installed.')
        else:
            for repo in repos:
                if repo['dirty']:
                    raise RuntimeError('EnforceClean: Uncommited changes in '
                                       'the "{}" repository.'.format(repo))


class PrintConfigOption(CommandLineOption):
    """Always print the configuration first."""

    def apply(self, args, run):
        print_config(run)
        print('-' * 79)


class NameOption(CommandLineOption):
    """Set the name for this run."""

    def __init__(self):
        super().__init__(arg='NAME',
                         arg_description='Name for this run.')

    def apply(self, args, run):
        run.experiment_info['name'] = args
        run.run_logger = run.root_logger.getChild(args)


class CaptureOption(CommandLineOption):
    """Control the way stdout and stderr are captured."""

    def __init__(self):
        super().__init__(short_flag = 'C',
                         arg='CAPTURE_MODE',
                         arg_description="stdout/stderr capture mode. "
                                         "One of [no, sys, fd]")

    def apply(self, args, run):
        run.capture_mode = args
