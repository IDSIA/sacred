#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from collections import OrderedDict
import inspect
import os.path
import sys
from host_info import get_module_versions
from run import Run
from sacred.arg_parser import get_config_updates, get_observers, parse_args
from sacred.captured_function import CapturedFunction
from sacred.commands import print_config, _flatten_keys
from sacred.config_scope import ConfigScope
from sacred.utils import create_basic_stream_logger
from sacred.host_info import get_host_info


class Experiment(object):
    def __init__(self, name=None, logger=None):
        self.name = name
        self.logger = logger
        self.cfgs = []
        self.main_function = None
        self.doc = None
        self.observers = []
        self._captured_functions = []
        self._commands = OrderedDict()
        self._commands['print_config'] = print_config

    ############################## Decorators ##################################

    def command(self, f):
        self._commands[f.__name__] = self.capture(f)
        return f

    def config(self, f):
        self.cfgs.append(ConfigScope(f))
        return self.cfgs[-1]

    def capture(self, f):
        if f in self._captured_functions:
            return f
        captured_function = CapturedFunction(f)
        self._captured_functions.append(captured_function)
        return captured_function

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
        f = self.main_function._wrapped_function
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

    def run(self, config_updates=None):
        cfg = self._set_up(config_updates)
        run = Run(self.main_function, cfg, self.observers, self.logger)
        self._emit_run_created_event()
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
        cfg = self._set_up_config(config_updates)
        self._set_up_captured_functions(cfg)
        return cfg

    def _set_up_captured_functions(self, config):
        assert self.logger is not None
        for cf in self._captured_functions:
            cf.logger = self.logger.getChild(cf.__name__)
            cf.config = config

    def _set_up_config(self, config_updates=None):
        config_updates = {} if config_updates is None else config_updates
        current_cfg = {}
        for config in self.cfgs:
            config(config_updates, preset=current_cfg)
            current_cfg.update(config)
        return current_cfg

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