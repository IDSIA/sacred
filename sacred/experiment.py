#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from collections import OrderedDict
import inspect
import os.path
import sys
from host_info import get_module_versions
from run import Run, ModuleRunner
from sacred.arg_parser import get_config_updates, get_observers, parse_args
from sacred.captured_function import create_captured_function
from sacred.commands import print_config
from sacred.config_scope import ConfigScope
from sacred.host_info import get_host_info


class CircularDependencyError(Exception):
    pass


class Module(object):
    def __init__(self, prefix, modules=(), gen_seed=False):
        self.prefix = prefix
        self.cfgs = []
        #TODO: does this need to be a dict any longer?
        self.modules = OrderedDict()
        for m in modules:
            self.modules[m.prefix] = m
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
    def traverse_modules(self):
        if self._is_traversing:
            raise CircularDependencyError()
        else:
            self._is_traversing = True
        yield self, 0
        for prefix, module in self.modules.items():
            for sr, depth in module.traverse_modules():
                yield sr, depth + 1
        self._is_traversing = False

    def gather_submodules_topological(self):
        submodules = {}
        for sm, depth in self.traverse_modules():
            if sm not in submodules:
                submodules[sm] = depth
            else:
                submodules[sm] = max(submodules[sm], depth)
        sorted_submodules = sorted(submodules,
                                   key=lambda x: -submodules[x])
        return sorted_submodules

    def create_module_runner(self, subrunner_cache):
        subrunners = [subrunner_cache[m] for m in self.modules.values()]
        r = ModuleRunner(self.cfgs,
                         subrunners=subrunners,
                         prefix=self.prefix,
                         captured_functions=self.captured_functions,
                         generate_seed=self.gen_seed)
        return r


# TODO: Is there a way of expressing the logger and the seeder as a module?
# TODO: Do we want that?
# TODO: Should 'main' be just a regular command?
# TODO: schould experiments be allowed a prefix? This might make them fully
# TODO: reusable as modules but might complicate things


class Experiment(Module):
    def __init__(self, name=None, modules=()):
        super(Experiment, self).__init__(prefix='',
                                         modules=modules,
                                         gen_seed=True)
        self.name = name
        self.main_function = None
        self.doc = None
        self.observers = []
        self._commands = OrderedDict()
        self._commands['print_config'] = print_config
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
        host_info = get_host_info()
        return dict(
            name=self.name,
            mainfile=mainfile,
            dependencies=dependencies,
            doc=self.doc,
            host_info=host_info
        )

    def run_commandline(self):
        args = parse_args(sys.argv,
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

        return self.run(config_updates, loglevel)

    def run_command(self, command_name, config_updates=None, loglevel=None):
        assert command_name in self._commands, \
            "Command '%s' not found" % command_name
        run = self.create_run(self._commands[command_name], observe=False)
        run.initialize(config_updates, loglevel)
        run.exrunner.logger.info("Running command '%s'" % command_name)
        return run(run)

    def create_run(self, main_func=None, observe=True):
        if main_func is None:
            main_func = self.main_function
        sorted_submodules = self.gather_submodules_topological()
        mod_runners = create_module_runners(sorted_submodules)
        observers = self.observers if observe else []
        run = Run(mod_runners[self], mod_runners.values(), main_func, observers)
        return run

    def run(self, config_updates=None, loglevel=None):
        run = self.create_run()
        run.initialize(config_updates, loglevel)
        self._emit_run_created_event()
        self.info = run.info   # FIXME: this is a hack to access the info
        run()
        return run

    ################### protected helpers ###################################

    def _emit_run_created_event(self):
        experiment_info = self.get_info()
        for o in self.observers:
            try:
                o.created_event(**experiment_info)
            except AttributeError:
                pass


def create_module_runners(sorted_submodules):
    subrunner_cache = OrderedDict()
    for sm in sorted_submodules:
        subrunner_cache[sm] = sm.create_module_runner(subrunner_cache)
    return subrunner_cache