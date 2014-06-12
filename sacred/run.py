#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from datetime import timedelta
import sys
import threading
import time
import traceback
from utils import create_rnd, get_seed


class CircularDependencyError(Exception):
    pass


class Status(object):
    SET_UP = 0
    STARTING = 1
    RUNNING = 2
    COMPLETED = 3
    INTERRUPTED = 4
    FAILED = 5


class ModuleRunner(object):
    def __init__(self, config_scopes, subrunners):
        self.status = Status.SET_UP
        self.config_scopes = config_scopes
        self.subrunners = subrunners
        self.config = None
        self.logger = None
        self._captured_functions = None
        self._is_traversing = False

    def get_subrunners_with_depth(self):
        if self._is_traversing:
            raise CircularDependencyError()
        else:
            self._is_traversing = True
        yield self, 0
        for prefix, subrunner in self.subrunners:
            sr, depth = subrunner.get_subrunners_with_depth()
            yield sr, depth + 1
        self._is_traversing = False


class Run(object):
    """
    Represents a single run of an experiment
    """

    def __init__(self, modrunner, main_function, config, observers, logger,
                 captured_functions):
        self.modrunner = modrunner
        self.main_function = main_function
        self.config = config
        self._observers = observers
        self.logger = logger
        self._captured_functions = captured_functions
        self.status = Status.SET_UP
        self.info = {}
        if 'seed' not in config:
            config['seed'] = get_seed()
        self._rnd = create_rnd(config['seed'])
        self._heartbeat = None
        self.captured_out = None
        self.start_time = None
        self.stop_time = None
        self.elapsed_time = None
        self.result = None

    def __call__(self):
        self.status = Status.RUNNING
        self._set_up_captured_functions()
        self._emit_started()
        self._start_heartbeat()
        try:
            self.result = self.main_function()
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

    def gather_subrunners(self):
        subrunners = {}
        for sr, depth in self.modrunner.get_subrunners_with_depth():
            if sr not in subrunners or subrunners[sr] < depth:
                subrunners[sr] = depth
        return sorted(subrunners, key=lambda x: -subrunners[x])

    def set_up_config(self, config_updates=None):
        config_updates = {} if config_updates is None else config_updates
        current_cfg = {}

        for prefix, mod in self.subrunners.items():
            config = mod.set_up_config(config_updates.get(prefix))
            current_cfg[prefix] = config

        for config in self.config_scopes:
            config(config_updates, preset=current_cfg)
            current_cfg.update(config)
        return current_cfg

    def _set_up_captured_functions(self):
        for cf in self._captured_functions:
            cf.logger = self.logger.getChild(cf.__name__)
            cf.config = self.config
            cf.seed = get_seed(self._rnd)
            cf.rnd = create_rnd(cf.seed)

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
        self.logger.info("Experiment started.")
        self.start_time = time.time()
        for o in self._observers:
            try:
                o.started_event(
                    start_time=self.start_time,
                    config=self.config)
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
            except AttributeError:
                pass

    def _stop_time(self):
        self.stop_time = time.time()
        elapsed_seconds = round(self.stop_time - self.start_time)
        self.elapsed_time = timedelta(seconds=elapsed_seconds)
        self.logger.info("Total time elapsed = %s", self.elapsed_time)
        return self.stop_time

    def _emit_completed(self, result):
        self.logger.info("Experiment completed.")
        stop_time = self._stop_time()
        for o in self._observers:
            try:
                o.completed_event(
                    stop_time=stop_time,
                    result=result)
            except AttributeError:
                pass

    def _emit_interrupted(self):
        self.logger.warning("Experiment aborted!")
        interrupt_time = self._stop_time()
        for o in self._observers:
            try:
                o.interrupted_event(
                    interrupt_time=interrupt_time)
            except AttributeError:
                pass

    def _emit_failed(self, etype, value, tb):
        self.logger.warning("Experiment failed!")
        fail_time = self._stop_time()
        fail_trace = traceback.format_exception(etype, value, tb)
        for o in self._observers:
            try:
                o.failed_event(
                    fail_time=fail_time,
                    fail_trace=fail_trace)
            except:  # _emit_failed should never throw
                pass
