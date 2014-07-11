#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from datetime import timedelta
import sys
import threading
import time
import traceback
from sacred.config_scope import dogmatize
from sacred.utils import tee_output
from sacred.commands import _flatten_keys
from utils import create_rnd, get_seed, create_basic_stream_logger


class Status(object):
    SET_UP = 0
    STARTING = 1
    RUNNING = 2
    COMPLETED = 3
    INTERRUPTED = 4
    FAILED = 5


def create_module_runners(sorted_submodules):
    subrunner_cache = {}
    for prefixes, sm in sorted_submodules:
        subrunner_cache[sm] = sm.create_module_runner(
            prefixes=prefixes,
            subrunner_cache=subrunner_cache)
    return subrunner_cache


class ModuleRunner(object):
    def __init__(self, config_scopes, subrunners, prefixes, captured_functions,
                 generate_seed):
        self.config_scopes = config_scopes
        self.subrunners = subrunners
        self.prefixes = sorted(prefixes, key=lambda x: len(x))
        self.canonical_prefix = prefixes[0]
        self.generate_seed = generate_seed
        self.config_updates = {}
        self.config = None
        self.logger = None
        self.seed = None
        self.rnd = None
        self._captured_functions = captured_functions

    def set_up_logging(self, level=None):
        if self.logger is not None:
            return

        if level:
            try:
                level = int(level)
            except ValueError:
                pass
        self.logger = create_basic_stream_logger(self.canonical_prefix,
                                                 level=level)
        self.logger.debug("No logger given. Created basic stream logger.")

    def distribute_config_updates(self, config_updates=None):
        config_updates = {} if config_updates is None else config_updates
        if not isinstance(config_updates, dict):
            self.logger.warning("Ignored attempt to overwrite module config "
                                "with %s." % config_updates)
        for k, v in config_updates.items():
            if k in self.subrunners:
                continue
            if k in self.config_updates:
                self.logger.warning("Conflicting update for %s: %s" % (k, v))
            else:
                self.config_updates[k] = v

        for prefix, subrunner in self.subrunners.items():
            subrunner.distribute_config_updates(config_updates.get(prefix))

    def set_up_seed(self, rnd=None):
        if self.seed is None:
            self.seed = self.config_updates.get('seed') or get_seed(rnd)
            self.rnd = create_rnd(self.seed)

        for prefix, subrunner in self.subrunners.items():
            subrunner.set_up_seed(self.rnd)

    def set_up_config(self):
        if self.config is not None:
            return self.config

        self.config = {}
        if self.generate_seed:
            self.config['seed'] = self.seed

        for prefix, subrunner in self.subrunners.items():
            # dogmatize to make the subrunner configurations read-only
            const_sub_config = dogmatize(subrunner.set_up_config())
            const_sub_config.revelation()
            self.config[prefix] = const_sub_config

        for config in self.config_scopes:
            config(self.config_updates, preset=self.config)
            self.config.update(config)

        # replace duplicate subrunner configurations with 'pointer-value'
        for prefix, subrunner in self.subrunners.items():
            full_path = (self.canonical_prefix + '.' + prefix).strip('.')
            if full_path != subrunner.canonical_prefix:
                del self.config[prefix]
                self.config[prefix] = '--> .' + subrunner.canonical_prefix

        return self.config

    def get_config_modifications(self):
        added = set()
        typechanges = {}
        updated = _flatten_keys(self.config_updates)
        for config in self.config_scopes:
            added |= config.added_values
            typechanges.update(config.typechanges)

        return added, updated, typechanges

    def finalize_initialization(self):
        # look at seed again, because it might have changed during the
        # configuration process
        if 'seed' in self.config:
            self.seed = self.config['seed']
            self.rnd = create_rnd(self.seed)

        for cf in self._captured_functions:
            cf.logger = self.logger.getChild(cf.__name__)
            cf.config = self.config
            cf.seed = get_seed(self.rnd)
            cf.rnd = create_rnd(cf.seed)

        self._warn_about_suspicious_changes()

    def _warn_about_suspicious_changes(self, ):
        add, upd, tch = self.get_config_modifications()
        for a in sorted(add):
            self.logger.warning('Added new config entry: "%s"' % a)
        for k, (t1, t2) in tch.items():
            if (isinstance(t1, type(None)) or
                    (t1 in (int, float) and t2 in (int, float))):
                continue
            self.logger.warning(
                'Changed type of config entry "%s" from %s to %s' %
                (k, t1.__name__, t2.__name__))


class Run(object):
    """
    Represents a single run of an experiment
    """

    def __init__(self, modrunner, subrunners, main_function, observers):
        self.modrunner = modrunner
        self.subrunners = subrunners
        self.main_function = main_function
        self._observers = observers
        self.status = Status.SET_UP
        self.info = {}
        self._heartbeat = None
        self.captured_out = None
        self.start_time = None
        self.stop_time = None
        self.elapsed_time = None
        self.result = None

    def initialize(self, config_updates=None, loglevel=None):
        for sr in self.subrunners:
            sr.set_up_logging(loglevel)

        self.modrunner.distribute_config_updates(config_updates)  # recursive
        self.modrunner.set_up_seed()  # recursive
        self.modrunner.set_up_config()  # recursive

        for sr in self.subrunners:
            sr.finalize_initialization()

        self.status = Status.STARTING

    def __call__(self, *args):
        with tee_output() as self.captured_out:
            self.status = Status.RUNNING
            self._emit_started()
            self._start_heartbeat()
            try:
                self.result = self.main_function(*args)
            except KeyboardInterrupt:
                self.status = Status.INTERRUPTED
                self._stop_heartbeat()
                self._emit_interrupted()
                raise
            except:
                self.status = Status.FAILED
                t, v, trace = sys.exc_info()
                self._stop_heartbeat()
                self._emit_failed(t, v, trace.tb_next)
                raise
            else:
                self.status = Status.COMPLETED
                self._stop_heartbeat()
                self._emit_completed(self.result)
                return self.result

    def _start_heartbeat(self):
        self._emit_heatbeat()
        self._heartbeat = threading.Timer(10, self._start_heartbeat)
        self._heartbeat.start()

    def _stop_heartbeat(self):
        if self._heartbeat is None:
            return
        self._heartbeat.cancel()
        self._heartbeat = None
        self._emit_heatbeat()  # one final beat to flush pending changes

    def _emit_started(self):
        self.modrunner.logger.info("Started.")
        self.start_time = time.time()
        for o in self._observers:
            try:
                o.started_event(
                    start_time=self.start_time,
                    config=self.modrunner.config)
            except AttributeError:
                pass

    def _emit_heatbeat(self):
        if self.status != Status.RUNNING:
            return

        for o in self._observers:
            try:
                o.heartbeat_event(
                    info=self.info,
                    captured_out=self.captured_out.getvalue())
                    # captured_out="")
            except AttributeError:
                pass

    def _stop_time(self):
        self.stop_time = time.time()
        elapsed_seconds = round(self.stop_time - self.start_time)
        self.elapsed_time = timedelta(seconds=elapsed_seconds)
        self.modrunner.logger.info("Total time elapsed = %s", self.elapsed_time)
        return self.stop_time

    def _emit_completed(self, result):
        self.modrunner.logger.info("Completed.")
        stop_time = self._stop_time()
        for o in self._observers:
            try:
                o.completed_event(
                    stop_time=stop_time,
                    result=result)
            except AttributeError:
                pass

    def _emit_interrupted(self):
        self.modrunner.logger.warning("Aborted!")
        interrupt_time = self._stop_time()
        for o in self._observers:
            try:
                o.interrupted_event(
                    interrupt_time=interrupt_time)
            except AttributeError:
                pass

    def _emit_failed(self, etype, value, tb):
        self.modrunner.logger.warning("Failed!")
        fail_time = self._stop_time()
        fail_trace = traceback.format_exception(etype, value, tb)
        for o in self._observers:
            try:
                o.failed_event(
                    fail_time=fail_time,
                    fail_trace=fail_trace)
            except:  # _emit_failed should never throw
                pass
