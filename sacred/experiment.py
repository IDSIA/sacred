#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from collections import OrderedDict
import inspect
import os.path
import sys

from sacred.arg_parser import get_config_updates, get_observers, parse_args
from sacred.captured_function import create_captured_function
from sacred.commands import print_config, print_dependencies
from sacred.config_files import load_config_file
from sacred.config_scope import ConfigScope, ConfigDict
from sacred.dependencies import gather_sources_and_dependencies
from sacred.initialize import create_run
from sacred.utils import print_filtered_stacktrace


__sacred__ = True  # marks files that should be filtered from stack traces


class CircularDependencyError(Exception):
    """
    This exception is thrown if the ingredients of the current experiment form
    a circular dependency.
    """


class Ingredient(object):
    """
    Ingredients are reusable parts of experiments. Each Ingredient can have its
    own configuration (visible as an entry in the parents configuration),
    named configurations, captured functions and commands.

    Ingredients can themselves use ingredients.
    """
    def __init__(self, path, ingredients=(), _generate_seed=False,
                 _caller_globals=None):
        self.path = path
        self.cfgs = []
        self.named_configs = dict()
        self.ingredients = list(ingredients)
        self.gen_seed = _generate_seed
        self.captured_functions = []
        self._is_traversing = False
        self.commands = OrderedDict()
        # capture some context information
        _caller_globals = _caller_globals or inspect.stack()[1][0].f_globals
        self.doc = _caller_globals.get('__doc__', "")
        self.sources, self.dependencies = \
            gather_sources_and_dependencies(_caller_globals)

    # =========================== Decorators ==================================
    def command(self, function=None, prefix=None):
        """
        Decorator to define a new command for this Ingredient or Experiment.

        The name of the command will be the name of the function. It can be
        called from the command-line or by using the run_command function.

        Commands are automatically also captured functions.

        The command can be given a prefix, to restrict its configuration space
        to a subtree. (see ``capture`` for more information)
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
        Decorator to turn a function into a
        :class:`~sacred.config_scope.ConfigScope` and add it to the
        Ingredient/Experiment.

        When the experiment is run, this function will also be executed and
        all json-serializable local variables inside it will end up as entries
        in the configuration of the experiment.
        """
        self.cfgs.append(ConfigScope(function))
        return self.cfgs[-1]

    def named_config(self, func):
        """
        Decorator to turn a function into a named configuration.
        See :ref:`named_configurations`.
        """
        config_scope = ConfigScope(func)
        self.named_configs[func.__name__] = config_scope
        return config_scope

    def capture(self, function=None, prefix=None):
        """
        Decorator to turn a function into a captured function.

        The missing arguments of captured functions are automatically filled
        from the configuration if possible.
        See :ref:`captured_functions` for more information.

        If a ``prefix`` is specified, the search for suitable
        entries is performed in the corresponding subtree of the configuration.
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

    # =========================== Public Interface ============================

    def add_config(self, cfg=None, **kw_conf):
        """
        Add a configuration entry to this ingredient/experiment. Can be called
        either with a dictionary or with keyword arguments.

        The dictionary or the keyword arguments will be converted into a
        :class:`~sacred.config_scope.ConfigDict`.

        :param cfg: Configuration dictionary to add to this
                    ingredient/experiment.
        :type cfg: dict
        :param kw_conf: Configuration entries to be added to this
                        ingredient/experiment.
        """
        if cfg is not None and kw_conf:
            raise ValueError("cannot combine keyword config with "
                             "positional argument")
        if cfg is None:
            if not kw_conf:
                raise ValueError("attempted to add empty config")
            self.cfgs.append(ConfigDict(kw_conf))
        elif isinstance(cfg, dict):
            self.cfgs.append(ConfigDict(cfg))
        else:
            raise TypeError("Invalid argument type {}".format(type(cfg)))

    def add_config_file(self, filename):
        """
        Add the contents of a configuration file to the configuration of this
        experiment. Supported formats so far are: ``json``, ``pickle`` and
        ``yaml``.

        :param filename: The filename of the configuration file to be loaded.
                         Has to have the appropriate file-ending.
        :type filename: str
        """
        if not os.path.exists(filename):
            raise IOError('File not found {}'.format(filename))
        abspath = os.path.abspath(filename)
        conf_dict = load_config_file(abspath)
        self.add_config(conf_dict)

    # ======================== Private Helpers ================================

    def _traverse_ingredients(self):
        if self._is_traversing:
            raise CircularDependencyError()
        else:
            self._is_traversing = True
        yield self, 0
        for ingredient in self.ingredients:
            for ingred, depth in ingredient._traverse_ingredients():
                yield ingred, depth + 1
        self._is_traversing = False

    def create_run_for_command(self, command_name, config_updates=None,
                               named_configs_to_use=(), loglevel=None):
        run = create_run(self, command_name, config_updates,
                         log_level=loglevel,
                         named_configs=named_configs_to_use)
        return run

    def run_command(self, command_name, config_updates=None,
                    named_configs_to_use=(), loglevel=None):
        run = self.create_run_for_command(command_name, config_updates,
                                          named_configs_to_use, loglevel)
        run.logger.info("Running command '%s'" % command_name)
        run()
        return run

    def _gather_commands(self):
        for cmd_name, cmd in self.commands.items():
            yield self.path + '.' + cmd_name, cmd

        for ingred in self.ingredients:
            for cmd_name, cmd in ingred._gather_commands():
                yield cmd_name, cmd


class Experiment(Ingredient):
    """
    An instance of this class builds the central piece of every experiment run
    in Sacred. It manages the configuration, the main function,
    captured methods, observers, commands, and further ingredients.

    An Experiment instance should be created as one of the first
    things in any experiment-file.
    """
    def __init__(self, name, ingredients=()):
        """
        Creates a new experiment with the given name and optional ingredients.

        :param name: name of this experiment
        :type name: str
        :param ingredients: a list of ingredients to be used with this
                            experiment.
        """
        caller_globals = inspect.stack()[1][0].f_globals
        super(Experiment, self).__init__(path=name,
                                         ingredients=ingredients,
                                         _generate_seed=True,
                                         _caller_globals=caller_globals)
        self.name = name
        self.default_command = None
        self.logger = None
        self.observers = []
        self.command(print_config)
        self.command(print_dependencies)
        self.info = None

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
        Decorator that defines the main function of the experiment and
        automatically runs the experiments command-line when the file is
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

    # =========================== Public Interface ============================

    def run(self, config_updates=None, named_configs=(), loglevel=None):
        """
        Run the main function of the experiment.

        :param config_updates: Changes to the configuration as a nested
                               dictionary
        :type config_updates: dict
        :param named_configs: list of names of named_configs to use
        :type named_configs: list[str]
        :param loglevel: Changes to the log-level for this run.
        :type loglevel: int | str

        :return: The result of the main function.
        """
        return self.run_command(self.default_command,
                                config_updates=config_updates,
                                named_configs_to_use=named_configs,
                                loglevel=loglevel)

    def run_commandline(self, argv=None):
        """
        Run the command-line interface of this experiment. If ``argv`` is
        omitted it defaults to ``sys.argv``.

        :param argv: split command-line like ``sys.argv``.
        :type argv: list[str]
        :return: The result of the command that was run.
        """
        if argv is None:
            argv = sys.argv
        all_commands = self._gather_commands()

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
                import traceback
                import pdb
                traceback.print_exception(*sys.exc_info())
                pdb.post_mortem()
            else:
                print_filtered_stacktrace()

    # =========================== Private Helpers =============================

    def _gather_commands(self):
        for cmd_name, cmd in self.commands.items():
            yield cmd_name, cmd

        for ingred in self.ingredients:
            for cmd_name, cmd in ingred._gather_commands():
                yield cmd_name, cmd

    def _get_info(self):
        dependencies = set()
        sources = set()
        for ing, _ in self._traverse_ingredients():
            dependencies |= ing.dependencies
            sources |= ing.sources

        for dep in dependencies:
            dep.fill_missing_version()

        return dict(
            sources=[s.to_tuple() for s in sorted(sources)],
            dependencies=[d.to_tuple() for d in sorted(dependencies)],
            doc=self.doc)
