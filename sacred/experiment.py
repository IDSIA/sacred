#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from collections import OrderedDict
import inspect
import os.path
import sys
import traceback as tb
from host_info import fill_missing_versions

from sacred.arg_parser import get_config_updates, get_observers, parse_args
from sacred.captured_function import create_captured_function
from sacred.commands import print_config
from sacred.config_scope import ConfigScope
from sacred.host_info import get_dependencies
from sacred.initialize import create_run


__sacred__ = True  # marker for filtering stacktraces when run from commandline


class CircularDependencyError(Exception):
    pass


class Ingredient(object):
    def __init__(self, path, ingredients=(), gen_seed=False,
                 caller_globals=None):
        self.path = path
        self.cfgs = []
        self.ingredients = list(ingredients)
        self.gen_seed = gen_seed
        self.captured_functions = []
        self._is_traversing = False
        caller_globals = caller_globals or inspect.stack()[1][0].f_globals
        self.doc = caller_globals.get('__doc__') or ""
        self.mainfile = caller_globals.get('__file__') or ""
        if self.mainfile:
            self.mainfile = os.path.abspath(self.mainfile)
        self.dependencies = get_dependencies(caller_globals)

    ############################## Decorators ##################################
    # def command(self, f):
    #     self._commands[f.__name__] = self.capture(f)
    #     return f

    def config(self, f):
        self.cfgs.append(ConfigScope(f))
        return self.cfgs[-1]

    def capture(self, f):
        if f in self.captured_functions:
            return f
        captured_function = create_captured_function(f)
        self.captured_functions.append(captured_function)
        return captured_function

    ################### protected helpers ###################################
    def traverse_ingredients(self):
        if self._is_traversing:
            raise CircularDependencyError()
        else:
            self._is_traversing = True
        yield self, 0
        for ingredient in self.ingredients:
            for sr, depth in ingredient.traverse_ingredients():
                yield sr, depth + 1
        self._is_traversing = False


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
        self._commands = OrderedDict()
        self.command(print_config)
        self.info = None

    ############################## Decorators ##################################

    def command(self, f):
        captured_f = self.capture(f)
        self._commands[f.__name__] = captured_f
        return captured_f

    def main(self, f):
        self.default_command = self.command(f)
        return self.default_command

    def automain(self, f):
        captured = self.main(f)
        if f.__module__ == '__main__':
            self.run_commandline()
        return captured

    ############################## public interface ############################

    def get_info(self):
        fill_missing_versions(self.dependencies)

        return dict(
            name=self.name,
            mainfile=self.mainfile,
            dependencies=self.dependencies,
            doc=self.doc)

    def run_commandline(self, argv=None):
        if argv is None:
            argv = sys.argv

        args = parse_args(argv,
                          description=self.doc,
                          commands=self._commands,
                          print_help=True)
        config_updates = get_config_updates(args['UPDATE'])
        loglevel = args.get('--logging')
        if args['COMMAND']:
            cmd_name = args['COMMAND']
            return self.run_command(cmd_name,
                                    config_updates=config_updates,
                                    loglevel=loglevel)

        for obs in get_observers(args):
            if obs not in self.observers:
                self.observers.append(obs)
        try:
            return self.run(config_updates, loglevel)
        except:
            if args['--debug']:
                raise
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print("Traceback (most recent calls WITHOUT sacred internals):",
                  file=sys.stderr)
            current_tb = exc_traceback
            while current_tb is not None:
                if '__sacred__' not in current_tb.tb_frame.f_globals:
                    tb.print_tb(current_tb, 1)
                current_tb = current_tb.tb_next
            tb.print_exception(exc_type, exc_value, None)

    def run_command(self, command_name, config_updates=None, loglevel=None):
        assert command_name in self._commands, \
            "Command '%s' not found" % command_name
        run = create_run(self, self._commands[command_name], config_updates,
                         log_level=loglevel)
        run.logger.info("Running command '%s'" % command_name)
        return run()

    def run(self, config_updates=None, loglevel=None):
        run = create_run(self, self.default_command, config_updates,
                         log_level=loglevel)
        return run()
