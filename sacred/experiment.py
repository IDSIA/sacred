#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from collections import OrderedDict
import inspect
import os.path
import sys
from initialize import create_run

from sacred.arg_parser import get_config_updates, get_observers, parse_args
from sacred.captured_function import create_captured_function
from sacred.commands import print_config
from sacred.config_scope import ConfigScope
from sacred.host_info import get_module_versions


__sacred__ = True  # marker for filtering stacktraces when run from commandline


class CircularDependencyError(Exception):
    pass


class Ingredient(object):
    def __init__(self, path, ingredients=(), gen_seed=False):
        self.path = path
        self.cfgs = []
        self.ingredients = list(ingredients)
        self.gen_seed = gen_seed
        self.captured_functions = []
        self._is_traversing = False

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
        super(Experiment, self).__init__(path='',
                                         ingredients=ingredients,
                                         gen_seed=True)
        self.name = name
        self.main_function = None
        self.logger = None
        self.doc = None
        self.observers = []
        self._commands = OrderedDict()
        self.command(print_config)
        self.info = None

    ############################## Decorators ##################################

    def command(self, f):
        self._commands[f.__name__] = self.capture(f)
        return f

    def main(self, f):
        self.doc = inspect.getmodule(f).__doc__ or ""
        self.main_function = self.capture(f)
        return self.main_function

    def automain(self, f):
        captured = self.main(f)
        if f.__module__ == '__main__':
            self.run_commandline()
        return captured

    ############################## public interface ############################

    def get_info(self):
        f = self.main_function
        mainfile = inspect.getabsfile(f)
        dependencies = get_module_versions(f.__globals__)
        if self.name is None:
            filename = os.path.basename(mainfile)
            self.name = filename.rsplit('.', 1)[0]
        return dict(
            name=self.name,
            mainfile=mainfile,
            dependencies=dependencies,
            doc=self.doc,
        )

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
            import traceback as tb
            print("Traceback (most recent calls WITHOUT sacred internals):",
                  file=sys.stderr)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            current_tb = exc_traceback
            while current_tb is not None:
                if '__sacred__' not in current_tb.tb_frame.f_globals:
                    tb.print_tb(current_tb, 1)
                current_tb = current_tb.tb_next
            tb.print_exception(exc_type, exc_value, None)
            pass

    def run_command(self, command_name, config_updates=None, loglevel=None):
        assert command_name in self._commands, \
            "Command '%s' not found" % command_name
        run = create_run(self, config_updates, self._commands[command_name],
                         observe=False, log_level=loglevel)
        run.logger.info("Running command '%s'" % command_name)
        return run()

    def run(self, config_updates=None, loglevel=None):
        run = create_run(self, config_updates, log_level=loglevel)
        return run()
