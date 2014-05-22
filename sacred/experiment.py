#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from collections import OrderedDict
from datetime import timedelta
import inspect
import os.path
import sys
import threading
import time
import traceback
from host_info import get_module_versions
from sacred.arg_parser import get_config_updates, get_observers, parse_args
from sacred.captured_function import CapturedFunction
from sacred.commands import print_config, _flatten_keys
from sacred.config_scope import ConfigScope
from sacred.utils import create_basic_stream_logger, tee_output


class Experiment(object):
    INITIALIZING, RUNNING, COMPLETED, INTERRUPTED, FAILED = range(5)

    def __init__(self, name=None, config=None, logger=None):
        self.cfg = config
        self.cfgs = []
        self._status = Experiment.INITIALIZING
        self._main_function = None
        self._captured_functions = []
        self._observers = []
        self.logger = logger
        self.name = name
        self.doc = None
        self.mainfile = None
        self.cmd = OrderedDict()
        self.cmd['print_config'] = print_config
        self.captured_out = None
        self._heartbeat = None
        self._dependencies = None
        self.info = {}
        self.description = {
            'seed': None,
            'start_time': None,
            'stop_time': None
        }

    ############################## Decorators ##################################

    def command(self, f):
        self.cmd[f.__name__] = self.capture(f)
        return f

    def config(self, f):
        self.cfgs.append(ConfigScope(f))
        return self.cfgs[-1]

    def capture(self, f):
        if f in self._captured_functions:
            return f
        captured_function = CapturedFunction(f, self)
        self._captured_functions.append(captured_function)
        return captured_function

    def main(self, f):
        self._main_function = self.capture(f)
        self.mainfile = inspect.getabsfile(f)
        self._dependencies = get_module_versions(f.__globals__)

        if self.name is None:
            filename = os.path.basename(self.mainfile)
            self.name = filename.rsplit('.', 1)[0]

        self.doc = inspect.getmodule(f).__doc__ or ""

        return self._main_function

    def automain(self, f):
        captured = self.main(f)
        if f.__module__ == '__main__':
            self.run_commandline()
        return captured

    ############################## public interface ############################

    def print_config(self, config_updates):
        self.reset()
        self._set_up_config(config_updates)
        import json
        print(json.dumps(self.cfg, indent=2, ))

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
                          commands=self.cmd,
                          print_help=True)
        config_updates = get_config_updates(args['UPDATE'])
        if args['--logging']:
            self._set_up_logging(args['--logging'])

        if args['COMMAND']:
            cmd_name = args['COMMAND']
            if cmd_name == 'print_config':
                self._set_up_logging()
                self._set_up_config(config_updates)
                add, upd, tch = self.get_config_modifications(config_updates)
                return print_config(self.cfg, add, upd, tch)
            else:
                return self.run_command(cmd_name,
                                        config_updates=config_updates)

        for obs in get_observers(args):
            self.add_observer(obs)

        return self.run(config_updates)

    def run_command(self, command_name, config_updates=None):
        self._set_up_logging()
        self._set_up_config(config_updates)
        assert command_name in self.cmd, "command '%s' not found" % command_name
        self.logger.info("Running command '%s'" % command_name)
        return self.cmd[command_name]()

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

    def run(self, config_updates=None):
        self.reset()
        with tee_output() as self.captured_out:
            self._set_up_config(config_updates)
            self._set_up_logging()
            self._warn_about_suspicious_changes(config_updates)
            self._status = Experiment.RUNNING
            self._emit_started()
            self._start_heartbeat()
            try:
                result = self._main_function()
            except KeyboardInterrupt:
                self._status = Experiment.INTERRUPTED
                self._emit_interrupted()
                raise
            except:
                self._status = Experiment.FAILED
                t, v, trace = sys.exc_info()
                self._emit_failed(t, v, trace.tb_next)
                raise
            else:
                self._status = Experiment.COMPLETED
                self._emit_completed(result)
                return result
            finally:
                self._heartbeat.cancel()

    def reset(self):
        self.info = {}
        self.description['seed'] = None
        self.description['start_time'] = None
        self.description['stop_time'] = None
        self.cfg = None
        self._status = Experiment.INITIALIZING

    ################### Observable interface ###################################
    def add_observer(self, obs):
        if not obs in self._observers:
            self._observers.append(obs)

    def remove_observer(self, obs):
        if obs in self._observers:
            self._observers.remove(obs)

    def _start_heartbeat(self):
        self._emit_info_updated()
        self._heartbeat = threading.Timer(10, self._start_heartbeat)
        self._heartbeat.start()

    def _emit_started(self):
        self.logger.info("Experiment started.")
        self.description['start_time'] = time.time()
        for o in self._observers:
            try:
                o.experiment_started_event(
                    name=self.name,
                    mainfile=self.mainfile,
                    doc=self.doc,
                    start_time=self.description['start_time'],
                    config=self.cfg,
                    info=self.info,
                    dependencies=self._dependencies)
            except AttributeError:
                pass

    def _emit_info_updated(self):
        if self._status != Experiment.RUNNING:
            return

        for o in self._observers:
            try:
                o.experiment_info_updated(
                    info=self.info,
                    captured_out=self.captured_out.getvalue())
            except AttributeError:
                pass

    def _stop_time(self):
        stop_time = time.time()
        self.description['stop_time'] = stop_time
        elapsed_seconds = round(stop_time - self.description['start_time'])
        elapsed_time = timedelta(seconds=elapsed_seconds)
        self.logger.info("Total time elapsed = %s", elapsed_time)
        return stop_time

    def _emit_completed(self, result):
        self.logger.info("Experiment completed.")
        stop_time = self._stop_time()
        for o in self._observers:
            try:
                o.experiment_completed_event(
                    stop_time=stop_time,
                    result=result,
                    info=self.info,
                    captured_out=self.captured_out.getvalue())
            except AttributeError:
                pass

    def _emit_interrupted(self):
        self.logger.warning("Experiment aborted!")
        interrupt_time = self._stop_time()
        for o in self._observers:
            try:
                o.experiment_interrupted_event(
                    interrupt_time=interrupt_time,
                    info=self.info,
                    captured_out=self.captured_out.getvalue())
            except AttributeError:
                pass

    def _emit_failed(self, etype, value, tb):
        self.logger.warning("Experiment failed!")
        fail_time = self._stop_time()
        fail_trace = traceback.format_exception(etype, value, tb)
        for o in self._observers:
            try:
                o.experiment_failed_event(
                    fail_time=fail_time,
                    fail_trace=fail_trace,
                    info=self.info,
                    captured_out=self.captured_out.getvalue())
            except:  # _emit_failed should never throw
                pass

    ################### protected helpers ###################################
    def _set_up_logging(self, level=None):
        if level:
            try:
                level = int(level)
            except ValueError:
                pass

        if self.logger is None:
            self.logger = create_basic_stream_logger(self.name, level=level)
            self.logger.debug("No logger given. Created basic stream logger.")
        for cf in self._captured_functions:
            cf.logger = self.logger.getChild(cf.__name__)

    def _set_up_config(self, config_updates=None):
        config_updates = {} if config_updates is None else config_updates
        assert self.cfg is None
        current_cfg = {}
        for config in self.cfgs:
            config(config_updates, preset=current_cfg)
            current_cfg.update(config)
        self.cfg = current_cfg