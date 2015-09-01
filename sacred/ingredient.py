#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import inspect
import os.path

from collections import OrderedDict

from sacred.config import (ConfigDict, ConfigScope, create_captured_function,
                           load_config_file)
from sacred.dependencies import (PEP440_VERSION_PATTERN, PackageDependency,
                                 Source, gather_sources_and_dependencies)
from sacred.initialize import create_run
from sacred.utils import CircularDependencyError, optional_kwargs_decorator

__sacred__ = True  # marks files that should be filtered from stack traces

__all__ = ('Ingredient',)


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
        self.config_hooks = []
        self.configurations = []
        self.named_configs = dict()
        self.ingredients = list(ingredients)
        self.logger = None
        self.observers = []
        self.captured_functions = []
        self.post_run_hooks = []
        self.pre_run_hooks = []
        self._is_traversing = False
        self.commands = OrderedDict()
        # capture some context information
        _caller_globals = _caller_globals or inspect.stack()[1][0].f_globals
        self.doc = _caller_globals.get('__doc__', "")
        self.sources, self.dependencies = \
            gather_sources_and_dependencies(_caller_globals)
        self.current_run = None

    # =========================== Decorators ==================================
    @optional_kwargs_decorator
    def capture(self, function=None, prefix=None):
        """
        Decorator to turn a function into a captured function.

        The missing arguments of captured functions are automatically filled
        from the configuration if possible.
        See :ref:`captured_functions` for more information.

        If a ``prefix`` is specified, the search for suitable
        entries is performed in the corresponding subtree of the configuration.
        """
        if function in self.captured_functions:
            return function
        captured_function = create_captured_function(function, prefix=prefix)
        self.captured_functions.append(captured_function)
        return captured_function

    @optional_kwargs_decorator
    def pre_run_hook(self, func, prefix=None):
        """
        Decorator to add a pre-run hook to this ingredient.

        Pre-run hooks are captured functions that are run, just before the
        main function is executed.
        """
        cf = self.capture(func, prefix=prefix)
        self.pre_run_hooks.append(cf)
        return cf

    @optional_kwargs_decorator
    def post_run_hook(self, func, prefix=None):
        """
        Decorator to add a post-run hook to this ingredient.

        Post-run hooks are captured functions that are run, just after the
        main function is executed.
        """
        cf = self.capture(func, prefix=prefix)
        self.post_run_hooks.append(cf)
        return cf

    @optional_kwargs_decorator
    def command(self, function=None, prefix=None):
        """
        Decorator to define a new command for this Ingredient or Experiment.

        The name of the command will be the name of the function. It can be
        called from the command-line or by using the run_command function.

        Commands are automatically also captured functions.

        The command can be given a prefix, to restrict its configuration space
        to a subtree. (see ``capture`` for more information)
        """
        captured_f = self.capture(function, prefix=prefix)
        self.commands[function.__name__] = captured_f
        return captured_f

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
        self.configurations.append(ConfigScope(function))
        return self.configurations[-1]

    def named_config(self, func):
        """
        Decorator to turn a function into a named configuration.

        See :ref:`named_configurations`.
        """
        config_scope = ConfigScope(func)
        self.named_configs[func.__name__] = config_scope
        return config_scope

    def config_hook(self, func):
        """
        Decorator to add a config hook to this ingredient.

        Config hooks need to be a function that takes 3 parameters and returns
        a dictionary:
        (config, command_name, logger) --> dict

        Config hooks are run after the configuration of this Ingredient, but
        before any further ingredient-configurations are run.
        The dictionary returned by a config hook is used to update the
        config updates.
        Note that they are not restricted to the local namespace of the
        ingredient.
        """
        argspec = inspect.getargspec(func)
        args = ['config', 'command_name', 'logger']
        if not (argspec.args == args and argspec.varargs is None and
                argspec.keywords is None and argspec.defaults is None):
            raise ValueError('Wrong signature for config_hook. Expected: '
                             '(config, command_name, logger)')
        self.config_hooks.append(func)
        return self.config_hooks[-1]

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
            self.configurations.append(ConfigDict(kw_conf))
        elif isinstance(cfg, dict):
            self.configurations.append(ConfigDict(cfg))
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
                    named_configs_to_use=()):
        """Run the command with the given name.

        :param command_name: Name of the command to be run
        :type command_name: str
        :param config_updates: a dictionary of parameter values that should
                               be updates (optional)
        :type config_updates: dict
        :param named_configs_to_use: list of names of named configurations to
                                     use (optional)
        :type named_configs_to_use: list[str]
        :returns: the Run object corresponding to the finished run
        :rtype: sacred.run.Run
        """
        run = self._create_run_for_command(command_name, config_updates,
                                           named_configs_to_use)
        self.current_run = run
        self.current_run.run_logger.info("Running command '%s'" % command_name)
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
                                named_configs_to_use=()):
        run = create_run(self, command_name, config_updates,
                         named_configs=named_configs_to_use)
        return run

    def _gather_commands(self):
        for cmd_name, cmd in self.commands.items():
            yield self.path + '.' + cmd_name, cmd

        for ingred in self.ingredients:
            for cmd_name, cmd in ingred._gather_commands():
                yield cmd_name, cmd
