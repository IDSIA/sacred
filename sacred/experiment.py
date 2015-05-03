#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import inspect
import os.path
import sys
from collections import OrderedDict

from sacred.arg_parser import get_config_updates, get_observers, parse_args
from sacred.commands import print_config, print_dependencies
from sacred.config import (ConfigDict, ConfigScope, create_captured_function,
                           load_config_file)
from sacred.dependencies import (PEP440_VERSION_PATTERN, PackageDependency,
                                 Source, gather_sources_and_dependencies)
from sacred.initialize import create_run
from sacred.utils import print_filtered_stacktrace, CircularDependencyError

__sacred__ = True  # marks files that should be filtered from stack traces


class Ingredient(object):

    """
    Ingredients are reusable parts of experiments.

    Each Ingredient can have its own configuration (visible as an entry in the
    parents configuration), named configurations, captured functions and
    commands.

    Ingredients can themselves use ingredients.
    """

    def __init__(self, path, ingredients=(), _caller_globals=None):
        self.path = path
        self.cfgs = []
        self.named_configs = dict()
        self.ingredients = list(ingredients)
        self.logger = None
        self.observers = []
        self.captured_functions = []
        self._is_traversing = False
        self.commands = OrderedDict()
        # capture some context information
        _caller_globals = _caller_globals or inspect.stack()[1][0].f_globals
        self.doc = _caller_globals.get('__doc__', "")
        self.sources, self.dependencies = \
            gather_sources_and_dependencies(_caller_globals)
        self.current_run = None

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
        Decorator to add a function to the configuration of the Experiment.

        The decorated function is turned into a
        :class:`~sacred.config_scope.ConfigScope` and added to the
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
        Add a configuration entry to this ingredient/experiment.

        Can be called either with a dictionary or with keyword arguments.

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
        Read and add a configuration file to the configuration.

        Supported formats so far are: ``json``, ``pickle`` and ``yaml``.

        :param filename: The filename of the configuration file to be loaded.
                         Has to have the appropriate file-ending.
        :type filename: str
        """
        if not os.path.exists(filename):
            raise IOError('File not found {}'.format(filename))
        abspath = os.path.abspath(filename)
        conf_dict = load_config_file(abspath)
        self.add_config(conf_dict)

    def add_source_file(self, filename):
        """
        Add a file as source dependency to this experiment/ingredient.

        :param filename: filename of the source to be added as dependency
        :type filename: str
        """
        self.sources.add(Source.create(filename))

    def add_package_dependency(self, package_name, version):
        """
        Add a package to the list of dependencies.

        :param package_name: The name of the package dependency
        :type package_name: str
        :param version: The (minimum) version of the package
        :type version: str
        """
        if not PEP440_VERSION_PATTERN.match(version):
            raise ValueError('Invalid Version: "{}"'.format(version))
        self.dependencies.add(PackageDependency(package_name, version))

    def run_command(self, command_name, config_updates=None,
                    named_configs_to_use=(), log_level=None):
        """Run the command with the given name.

        :param command_name: Name of the command to be run
        :type command_name: str
        :param config_updates: a dictionary of parameter values that should
                               be updates (optional)
        :type config_updates: dict
        :param named_configs_to_use: list of names of named configurations to
                                     use (optional)
        :type named_configs_to_use: list[str]
        :param log_level: the log-level to use for this run either as integers
                         or strings (10 DEBUG - 50 CRITICAL)
        :type log_level: int | str
        :returns: whatever the command returned
        """
        run = self._create_run_for_command(
            command_name, config_updates, named_configs_to_use, log_level)
        self.current_run = run
        self.current_run.logger.info("Running command '%s'" % command_name)
        run()
        self.current_run = None
        return run

    def get_experiment_info(self):
        """Get a dictionary with information about this experiment.

        Contains:
          * *name*: the name
          * *sources*: a list of sources (filename, md5)
          * *dependencies*: a list of package dependencies (name, version)
          * *doc*: the docstring

        :return: experiment information
        :rtype: dict
        """
        dependencies = set()
        sources = set()
        for ing, _ in self._traverse_ingredients():
            dependencies |= ing.dependencies
            sources |= ing.sources

        for dep in dependencies:
            dep.fill_missing_version()

        return dict(
            name=self.path,
            sources=[s.to_tuple() for s in sorted(sources)],
            dependencies=[d.to_tuple() for d in sorted(dependencies)],
            doc=self.doc)

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

    def _create_run_for_command(self, command_name, config_updates=None,
                                named_configs_to_use=(), log_level=None):
        run = create_run(self, command_name, config_updates,
                         log_level=log_level,
                         named_configs=named_configs_to_use)
        return run

    def _gather_commands(self):
        for cmd_name, cmd in self.commands.items():
            yield self.path + '.' + cmd_name, cmd

        for ingred in self.ingredients:
            for cmd_name, cmd in ingred._gather_commands():
                yield cmd_name, cmd


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
        assert self.default_command, "No main function found"
        return self.run_command(self.default_command,
                                config_updates=config_updates,
                                named_configs_to_use=named_configs,
                                log_level=loglevel)

    def run_commandline(self, argv=None):
        """
        Run the command-line interface of this experiment.

        If ``argv`` is omitted it defaults to ``sys.argv``.

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
                                    log_level=loglevel)
        except Exception:
            if args['--debug']:
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
