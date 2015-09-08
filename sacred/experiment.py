#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import inspect
import sys
from collections import OrderedDict

from sacred.arg_parser import get_config_updates, parse_args
from sacred.commandline_options import gather_command_line_options
from sacred.commands import print_config, print_dependencies
from sacred.ingredient import Ingredient
from sacred.utils import print_filtered_stacktrace

__sacred__ = True  # marks files that should be filtered from stack traces

__all__ = ('Experiment',)


class Experiment(Ingredient):

    """
    The central class for each experiment in Sacred.

    It manages the configuration, the main function, captured methods,
    observers, commands, and further ingredients.

    An Experiment instance should be created as one of the first
    things in any experiment-file.
    """

    def __init__(self, name, ingredients=()):
        """
        Create a new experiment with the given name and optional ingredients.

        :param name: name of this experiment
        :type name: str
        :param ingredients: a list of ingredients to be used with this
                            experiment.
        """
        caller_globals = inspect.stack()[1][0].f_globals
        super(Experiment, self).__init__(path=name,
                                         ingredients=ingredients,
                                         _caller_globals=caller_globals)
        self.default_command = ""
        self.command(print_config)
        self.command(print_dependencies)
        self.observers = []
        self.current_run = None

    # =========================== Decorators ==================================

    def main(self, function):
        """
        Decorator to define the main function of the experiment.

        The main function of an experiment is the default command that is being
        run when no command is specified, or when calling the run() method.

        Usually it is more convenient to use ``automain`` instead.
        """
        captured = self.command(function)
        self.default_command = captured.__name__
        return captured

    def automain(self, function):
        """
        Decorator that defines *and runs* the main function of the experiment.

        The decorated function is marked as the default command for this
        experiment, and the command-line interface is automatically run when
        the file is executed.

        The method decorated by this should be last in the file because is
        equivalent to:

        .. code-block:: python

            @ex.main
            def my_main():
                pass

            if __name__ == '__main__':
                ex.run_commandline()
        """
        captured = self.main(function)
        if function.__module__ == '__main__':
            self.run_commandline()
        return captured

    # =========================== Public Interface ============================

    def run(self, config_updates=None, named_configs=()):
        """
        Run the main function of the experiment.

        :param config_updates: Changes to the configuration as a nested
                               dictionary
        :type config_updates: dict
        :param named_configs: list of names of named_configs to use
        :type named_configs: list[str]

        :returns: the Run object corresponding to the finished run
        :rtype: sacred.run.Run
        """
        assert self.default_command, "No main function found"
        return self.run_command(self.default_command,
                                config_updates=config_updates,
                                named_configs_to_use=named_configs)

    def run_command(self, command_name, config_updates=None,
                    named_configs_to_use=(), args=()):
        """Run the command with the given name.

        :param command_name: Name of the command to be run
        :type command_name: str
        :param config_updates: a dictionary of parameter values that should
                               be updates (optional)
        :type config_updates: dict
        :param named_configs_to_use: list of names of named configurations to
                                     use (optional)
        :type named_configs_to_use: list[str]
        :param args: dictionary of command-line options
        :type args: dict
        :returns: the Run object corresponding to the finished run
        :rtype: sacred.run.Run
        """
        run = self._create_run_for_command(command_name, config_updates,
                                           named_configs_to_use)
        self.current_run = run
        for option in gather_command_line_options():
            op_name = '--' + option.get_flag()[1]
            if op_name in args:
                option.execute(args[op_name], run)
        self.current_run.run_logger.info("Running command '%s'" % command_name)
        run()
        self.current_run = None
        return run

    def run_commandline(self, argv=None):
        """
        Run the command-line interface of this experiment.

        If ``argv`` is omitted it defaults to ``sys.argv``.

        :param argv: split command-line like ``sys.argv``.
        :type argv: list[str]
        :returns: the Run object corresponding to the finished run
        :rtype: sacred.run.Run
        """
        if argv is None:
            argv = sys.argv
        all_commands = self._gather_commands()

        args = parse_args(argv,
                          description=self.doc,
                          commands=OrderedDict(all_commands))
        config_updates, named_configs = get_config_updates(args['UPDATE'])
        cmd_name = args.get('COMMAND') or self.default_command

        try:
            return self.run_command(cmd_name, config_updates, named_configs,
                                    args)
        except Exception:
            if self.current_run and self.current_run.debug:
                import traceback
                import pdb
                traceback.print_exception(*sys.exc_info())
                pdb.post_mortem()
            else:
                print_filtered_stacktrace()

    def open_resource(self, filename):
        """Open a file and also save it as a resource.

        Opens a file, reports it to the observers as a resource, and returns
        the opened file.

        In Sacred terminology a resource is a file that the experiment needed
        to access during a run. In case of a MongoObserver that means making
        sure the file is stored in the database (but avoiding duplicates) along
        its path and md5 sum.

        This function can only be called during a run, and just calls the
        :py:meth:`sacred.run.Run.open_resource` method.

        :param filename: name of the file that should be opened
        :type filename: str
        :return: the opened file-object
        :rtype: file
        """
        assert self.current_run is not None, "Can only be called during a run."
        return self.current_run.open_resource(filename)

    def add_artifact(self, filename):
        """Add a file as an artifact.

        In Sacred terminology an artifact is a file produced by the experiment
        run. In case of a MongoObserver that means storing the file in the
        database.

        This function can only be called during a run, and just calls the
        :py:meth:`sacred.run.Run.add_artifact` method.

        :param filename: name of the file to be stored as artifact
        :type filename: str
        """
        assert self.current_run is not None, "Can only be called during a run."
        self.current_run.add_artifact(filename)

    @property
    def info(self):
        """Access the info-dict for storing custom information.

        Only works during a run and is essentially a shortcut to:

        .. code-block:: python

            @ex.capture
            def my_captured_function(_run):
                # [...]
                _run.info   # == ex.info
        """
        return self.current_run.info

    # =========================== Private Helpers =============================

    def _gather_commands(self):
        for cmd_name, cmd in self.commands.items():
            yield cmd_name, cmd

        for ingred in self.ingredients:
            for cmd_name, cmd in ingred._gather_commands():
                yield cmd_name, cmd
