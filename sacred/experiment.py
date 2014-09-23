#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from collections import OrderedDict
import inspect
import os.path
import sys

from sacred.arg_parser import get_config_updates, get_observers, parse_args
from sacred.captured_function import create_captured_function
from sacred.commands import print_config
from sacred.config_scope import ConfigScope
from sacred.host_info import get_dependencies, fill_missing_versions
from sacred.initialize import create_run
from sacred.utils import print_filtered_stacktrace


__sacred__ = True  # marker for filtering stacktraces when run from commandline


class CircularDependencyError(Exception):
    pass


class Ingredient(object):
    def __init__(self, path, ingredients=(), gen_seed=False,
                 caller_globals=None):
        self.path = path
        self.cfgs = []
        self.named_configs = dict()
        self.ingredients = list(ingredients)
        self.gen_seed = gen_seed
        self.captured_functions = []
        self._is_traversing = False
        self.commands = OrderedDict()
        # capture some context information
        caller_globals = caller_globals or inspect.stack()[1][0].f_globals
        self.doc = caller_globals.get('__doc__') or ""
        self.mainfile = caller_globals.get('__file__') or ""
        if self.mainfile:
            self.mainfile = os.path.abspath(self.mainfile)
            if self.mainfile.endswith('.pyc'):
                non_compiled_mainfile = self.mainfile[:-1]
                if os.path.exists(non_compiled_mainfile):
                    self.mainfile = non_compiled_mainfile

        self.dependencies = get_dependencies(caller_globals)

    # =========================== Decorators ==================================
    def command(self, function=None, prefix=None):
        """
        Decorator to define a new command for this Ingredient or Experiment.

        The name of the command will be the name of the function. It can be
        called from the commandline or by using the run_command function.

        Commands are automatically also captured functions.
        """
        def _command(func):
            captured_f = self.capture(func, prefix=prefix)
            self.commands[func.__name__] = captured_f
            return captured_f

        if function is not None:
            return _command(function)
        else:
            return _command

    def config(self, function):
        """
        Decorator to turn a function into a ConfigScope and add it to the
        Ingredient/Experiment.
        """
        self.cfgs.append(ConfigScope(function))
        return self.cfgs[-1]

    def named_config(self, func):
        config_scope = ConfigScope(func)
        self.named_configs[func.__name__] = config_scope
        return config_scope

    def capture(self, function=None, prefix=None):
        """
        Decorator to turn a function into a captured function.
        """
        def _capture(func):
            if func in self.captured_functions:
                return func
            captured_function = create_captured_function(func, prefix=prefix)
            self.captured_functions.append(captured_function)
            return captured_function

        if function is not None:
            return _capture(function)
        else:
            return _capture

    # ======================== protected helpers ==============================
    def traverse_ingredients(self):
        if self._is_traversing:
            raise CircularDependencyError()
        else:
            self._is_traversing = True
        yield self, 0
        for ingredient in self.ingredients:
            for ingred, depth in ingredient.traverse_ingredients():
                yield ingred, depth + 1
        self._is_traversing = False

    def run_command(self, command_name, config_updates=None,
                    named_configs_to_use=(), loglevel=None):
        run = create_run(self, command_name, config_updates,
                         log_level=loglevel,
                         named_configs=named_configs_to_use)
        run.logger.info("Running command '%s'" % command_name)
        return run()

    def gather_commands(self):
        for cmd_name, cmd in self.commands.items():
            yield self.path + '.' + cmd_name, cmd

        for ingred in self.ingredients:
            for cmd_name, cmd in ingred.gather_commands():
                yield cmd_name, cmd


class Experiment(Ingredient):
    def __init__(self, name, ingredients=()):
        caller_globals = inspect.stack()[1][0].f_globals
        super(Experiment, self).__init__(path=name,
                                         ingredients=ingredients,
                                         gen_seed=True,
                                         caller_globals=caller_globals)
        self.name = name
        self.default_command = None
        self.logger = None
        self.observers = []
        self.command(print_config)
        self.info = None

    # =========================== Decorators ==================================

    def main(self, function):
        """
        Decorator to define the main function of the experiment.

        The main function of an experiment is the default command that is being
        run when no command is specified, or when calling the run() method.
        """
        captured = self.command(function)
        self.default_command = captured.__name__
        return captured

    def automain(self, function):
        """
        Decorator that defines the main function of the experiment and
        automatically runs the experiment commandline when the file is
        executed.

        The method decorated by this should be last in the file because:

        .. code-block:: python

            @ex.automain
            def my_main():
                pass

        is equivalent to:

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

    # =========================== public interface ============================

    def get_info(self):
        fill_missing_versions(self.dependencies)

        return dict(
            mainfile=self.mainfile,
            dependencies=self.dependencies.items(),
            doc=self.doc)

    def run(self, config_updates=None, named_configs=(), loglevel=None):
        """
        Run the main function of the experiment.

        :param config_updates: Changes to the configuration as a nested
                               dictionary
        :type config_updates: dict
        :param named_configs: list of names of named_configs to use
        :type named_configs: list
        :param loglevel: Changes to the log-level for this run.
        :type loglevel: int | str

        :return: The result of the main function.
        """
        return self.run_command(self.default_command,
                                config_updates=config_updates,
                                named_configs_to_use=named_configs,
                                loglevel=loglevel)

    def run_commandline(self, argv=None):
        if argv is None:
            argv = sys.argv
        all_commands = self.gather_commands()

        args = parse_args(argv,
                          description=self.doc,
                          commands=OrderedDict(all_commands))
        config_updates, named_configs = get_config_updates(args['UPDATE'])
        loglevel = args.get('--logging')
        for obs in get_observers(args):
            if obs not in self.observers:
                self.observers.append(obs)

        if args['COMMAND']:
            cmd_name = args['COMMAND']
        else:
            cmd_name = self.default_command

        try:
            return self.run_command(cmd_name,
                                    config_updates=config_updates,
                                    named_configs_to_use=named_configs,
                                    loglevel=loglevel)
        except:
            if args['--debug']:
                raise
            else:
                print_filtered_stacktrace()

    def gather_commands(self):
        for cmd_name, cmd in self.commands.items():
            yield cmd_name, cmd

        for ingred in self.ingredients:
            for cmd_name, cmd in ingred.gather_commands():
                yield cmd_name, cmd
