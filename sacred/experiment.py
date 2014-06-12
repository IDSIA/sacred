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
from sacred.commands import print_config, _flatten_keys
from sacred.config_scope import ConfigScope
from sacred.utils import create_basic_stream_logger
from sacred.host_info import get_host_info


class CircularDependencyError(Exception):
    pass


class Module(object):
    def __init__(self, prefix, modules=()):
        self.prefix = prefix
        self.cfgs = []
        self.modules = OrderedDict()
        for m in modules:
            self.modules[m.prefix] = m
        self._captured_functions = []
        self._is_setting_up_config = False
        self._is_traversing = False

    ############################## Decorators ##################################
    # def command(self, f):
    #     self._commands[f.__name__] = self.capture(f)
    #     return f

    def config(self, f):
        self.cfgs.append(ConfigScope(f))
        return self.cfgs[-1]

    def capture(self, f, as_name=None):
        if f in self._captured_functions:
            return f
        as_name = as_name or f.__name__
        if hasattr(self, as_name):
            raise AttributeError("Function name %s is already taken." %
                                 as_name)
        captured_function = create_captured_function(f)
        self._captured_functions.append(captured_function)
        setattr(self, as_name, captured_function)
        return captured_function

    ################### protected helpers ###################################
    def traverse_modules(self):
        if self._is_traversing:
            raise CircularDependencyError()
        else:
            self._is_traversing = True
        yield self.prefix, self, 0
        for prefix, module in self.modules.items():
            for p, sr, depth in module.traverse_modules():
                yield prefix + '.' + p, sr, depth + 1
        self._is_traversing = False

    def create_runner(self):
        submodules = {}
        for prefix, sm, depth in self.traverse_modules():
            if sm not in submodules:
                submodules[sm] = {'prefixes': [prefix], 'depth': depth}
            else:
                submodules[sm]['prefixes'].append(prefix)
                submodules[sm]['depth'] = max(submodules[sm]['depth'], depth)

        sorted_submodules = sorted(submodules,
                                   key=lambda x: -submodules[x]['depth'])
        subrunner_cache = {}
        for sm in sorted_submodules:
            subrunner_cache[sm] = ModuleRunner.from_module(
                sm,
                prefixes=submodules[sm]['prefixes'],
                subrunner_cache=subrunner_cache)

        return subrunner_cache[self]


# TODO: Figure out a good api for calling module commands
# TODO: figure out module equivalent of a Run
# TODO: Is there a way of expressing the logger and the seeder as a module? Do we want that?


class Experiment(Module):
    def __init__(self, name=None, logger=None, modules=()):
        super(Experiment, self).__init__(prefix=name, modules=modules)
        self.name = name
        self.logger = logger
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
        self.main_function = self.capture(f, "__main__")
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

    def get_config_modifications(self, config_updates):
        added = set()
        typechanges = {}
        updated = list(_flatten_keys(config_updates))
        for config in self.cfgs:
            added |= config.added_values
            typechanges.update(config.typechanges)
        return added, updated, typechanges

    def run_commandline(self):
        args = parse_args(sys.argv,
                          description=self.doc,
                          commands=self._commands,
                          print_help=True)
        config_updates = get_config_updates(args['UPDATE'])
        if args['--logging']:
            self._set_up_logging(args['--logging'])

        if args['COMMAND']:
            cmd_name = args['COMMAND']
            if cmd_name == 'print_config':
                cfg = self._set_up(config_updates)

                add, upd, tch = self.get_config_modifications(config_updates)
                return print_config(cfg, add, upd, tch)
            else:
                return self.run_command(cmd_name,
                                        config_updates=config_updates)

        for obs in get_observers(args):
            if obs not in self.observers:
                self.observers.append(obs)

        return self.run(config_updates)

    def run_command(self, command_name, config_updates=None):
        self._set_up(config_updates)
        assert command_name in self._commands, \
            "Command '%s' not found" % command_name
        self.logger.info("Running command '%s'" % command_name)
        return self._commands[command_name]()

    def _create_runner(self):
        pass

    def run(self, config_updates=None):
        runner = self.create_runner()

        cfg = self._set_up(config_updates)
        run = Run(self.main_function, cfg, self.observers, self.logger,
                  self._captured_functions)
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

    def _set_up(self, config_updates):
        self._set_up_logging()
        cfg = self.set_up_config(config_updates)
        return cfg

    def _set_up_logging(self, level=None):
        if level:
            try:
                level = int(level)
            except ValueError:
                pass

        if self.logger is None:
            self.logger = create_basic_stream_logger(self.name, level=level)
            self.logger.debug("No logger given. Created basic stream logger.")

    def _warn_about_suspicious_changes(self, config_updates):
        add, upd, tch = self.get_config_modifications(config_updates)
        for a in sorted(add):
            self.logger.warning('Added new config entry: "%s"' % a)
        for k, (t1, t2) in tch.items():
            if (isinstance(t1, type(None)) or
                    (t1 in (int, float) and t2 in (int, float))):
                continue
            self.logger.warning(
                'Changed type of config entry "%s" from %s to %s' %
                (k, t1.__name__, t2.__name__))

