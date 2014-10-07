#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from datetime import timedelta
import sys
import threading
import time
import traceback

from sacred.utils import tee_output


__sacred__ = True  # marker for filtering stacktraces when run from commandline


class Status(object):
    READY = 1
    RUNNING = 2
    COMPLETED = 3
    INTERRUPTED = 4
    FAILED = 5


class Run(object):
    """
    Represents and manages a single run of an experiment.
    """

    def __init__(self, config, config_modifications, main_function, observers,
                 logger, experiment_name, experiment_info, host_info):
        self.config = config
        self.main_function = main_function
        self.config_modifications = config_modifications
        self._observers = observers
        self.logger = logger
        self.experiment_name = experiment_name
        self.experiment_info = experiment_info
        self.host_info = host_info
        self.status = Status.READY
        self.info = {}
        self._heartbeat = None
        self.captured_out = None
        self.start_time = None
        self.stop_time = None
        self.elapsed_time = None
        self.result = None
        self._emit_run_created_event()

    def __call__(self, *args):
        with tee_output() as self.captured_out:
            self.logger.info('Started')
            self.status = Status.RUNNING
            self._emit_started()
            self._start_heartbeat()
            try:
                self.result = self.main_function(*args)
            except KeyboardInterrupt:
                self._stop_heartbeat()
                self.status = Status.INTERRUPTED
                self._emit_interrupted()
                raise
            except:
                exc_type, exc_value, trace = sys.exc_info()
                self._stop_heartbeat()
                self.status = Status.FAILED
                self._emit_failed(exc_type, exc_value, trace.tb_next)
                raise
            else:
                self._stop_heartbeat()
                self.status = Status.COMPLETED
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

    def _emit_run_created_event(self):
        for observer in self._observers:
            try:
                observer.created_event(**self.experiment_info)
            except AttributeError:
                pass

    def _emit_started(self):
        self.start_time = time.time()
        for observer in self._observers:
            try:
                observer.started_event(
                    name=self.experiment_name,
                    ex_info=self.experiment_info,
                    host_info=self.host_info,
                    start_time=self.start_time,
                    config=self.config)
            except AttributeError:
                pass

    def _emit_heatbeat(self):
        if self.status != Status.RUNNING:
            return

        for observer in self._observers:
            try:
                observer.heartbeat_event(
                    info=self.info,
                    captured_out=self.captured_out.getvalue())
            except AttributeError:
                pass

    def _stop_time(self):
        self.stop_time = time.time()
        elapsed_seconds = round(self.stop_time - self.start_time)
        self.elapsed_time = timedelta(seconds=elapsed_seconds)
        return self.stop_time

    def _emit_completed(self, result):
        stop_time = self._stop_time()
        self.logger.info('Completed after %s' % self.elapsed_time)
        for observer in self._observers:
            try:
                observer.completed_event(
                    stop_time=stop_time,
                    result=result)
            except AttributeError:
                pass

    def _emit_interrupted(self):
        interrupt_time = self._stop_time()
        self.logger.warning("Aborted after %s!" % self.elapsed_time)
        for observer in self._observers:
            try:
                observer.interrupted_event(
                    interrupt_time=interrupt_time)
            except AttributeError:
                pass

    def _emit_failed(self, exc_type, exc_value, trace):
        fail_time = self._stop_time()
        self.logger.error("Failed after %s!" % self.elapsed_time)
        fail_trace = traceback.format_exception(exc_type, exc_value, trace)
        for observer in self._observers:
            try:
                observer.failed_event(
                    fail_time=fail_time,
                    fail_trace=fail_trace)
            except:  # _emit_failed should never throw
                pass
