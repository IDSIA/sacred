#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
import sys
import threading
import time
from datetime import timedelta
import traceback


class Status(object):
    INITIALIZING = 0
    RUNNING = 1
    COMPLETED = 2
    INTERRUPTED = 3
    FAILED = 3


class Run(object):
    """
    Represents a single run of an experiment
    """

    def __init__(self, main_function, config, observers, logger):
        self.main_function = main_function
        self.cfg = config
        self._observers = observers
        self.logger = logger
        self.status = Status.INITIALIZING
        self.info = {}
        self._heartbeat = None
        self.captured_out = None
        self.start_time = None
        self.stop_time = None
        self.elapsed_time = None
        self.result = None

    def __call__(self):
        self.status = Status.RUNNING
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
                    config=self.cfg)
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