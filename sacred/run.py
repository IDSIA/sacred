#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import datetime
import os.path
import sys
import threading
import traceback

from sacred.randomness import set_global_seed
from sacred.utils import tee_output, ObserverError

__sacred__ = True  # marks files that should be filtered from stack traces


class Run(object):

    """Represent and manage a single run of an experiment."""

    def __init__(self, config, config_modifications, main_function, observers,
                 logger, experiment_info, host_info):
        self.config = config
        self.main_function = main_function
        self.config_modifications = config_modifications
        self._observers = observers
        self._failed_observers = set()
        self.logger = logger
        self.experiment_info = experiment_info
        self.host_info = host_info
        self.info = {}
        self._heartbeat = None
        self.captured_out = None
        self.start_time = None
        self.stop_time = None
        self.elapsed_time = None
        self.result = None

    def open_resource(self, filename):
        filename = os.path.abspath(filename)
        self._emit_resource_added(filename)  # TODO: maybe non-blocking?
        return open(filename, 'r')  # TODO: How to deal with binary mode?

    def add_artifact(self, filename):
        filename = os.path.abspath(filename)
        self._emit_artifact_added(filename)

    def __call__(self, *args):
        set_global_seed(self.config['seed'])
        with tee_output() as self.captured_out:
            self.logger.info('Started')
            self._emit_started()
            self._start_heartbeat()
            try:
                self.result = self.main_function(*args)
                self._stop_heartbeat()
                self._emit_completed(self.result)
                return self.result
            except KeyboardInterrupt:
                self._stop_heartbeat()
                self._emit_interrupted()
                raise
            except:
                exc_type, exc_value, trace = sys.exc_info()
                self._stop_heartbeat()
                self._emit_failed(exc_type, exc_value, trace.tb_next)
                raise
            finally:
                self._warn_about_failed_observers()

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
        self.start_time = datetime.datetime.now()
        for observer in self._observers:
            if hasattr(observer, 'started_event'):
                observer.started_event(
                    ex_info=self.experiment_info,
                    host_info=self.host_info,
                    start_time=self.start_time,
                    config=self.config)
                # do not catch any exceptions on startup the experiment should
                # fail if any of the observers fails

    def _emit_heatbeat(self):
        if self.start_time is None or self.stop_time is not None:
            return
        beat_time = datetime.datetime.now()
        for observer in self._observers:
            self._safe_call(observer, 'heartbeat_event',
                            info=self.info,
                            captured_out=self.captured_out.getvalue(),
                            beat_time=beat_time)

    def _stop_time(self):
        self.stop_time = datetime.datetime.now()
        self.elapsed_time = datetime.timedelta(
            seconds=round((self.stop_time - self.start_time).total_seconds()))
        return self.stop_time

    def _emit_completed(self, result):
        stop_time = self._stop_time()
        self.logger.info('Completed after %s' % self.elapsed_time)
        for observer in self._observers:
            self._final_call(observer, 'completed_event',
                             stop_time=stop_time,
                             result=result)

    def _emit_interrupted(self):
        interrupt_time = self._stop_time()
        self.logger.warning("Aborted after %s!" % self.elapsed_time)
        for observer in self._observers:
            self._final_call(observer, 'interrupted_event',
                             interrupt_time=interrupt_time)

    def _emit_failed(self, exc_type, exc_value, trace):
        fail_time = self._stop_time()
        self.logger.error("Failed after %s!" % self.elapsed_time)
        fail_trace = traceback.format_exception(exc_type, exc_value, trace)
        for observer in self._observers:
            self._final_call(observer, 'failed_event',
                             fail_time=fail_time,
                             fail_trace=fail_trace)

    def _emit_resource_added(self, filename):
        for observer in self._observers:
            self._safe_call(observer, 'resource_event', filename=filename)

    def _emit_artifact_added(self, filename):
        for observer in self._observers:
            self._safe_call(observer, 'artifact_event', filename=filename)

    def _safe_call(self, obs, method, **kwargs):
        if obs not in self._failed_observers and hasattr(obs, method):
            try:
                getattr(obs, method)(**kwargs)
            except ObserverError as e:
                self._failed_observers.add(obs)
                self.logger.warning("An error ocurred in the '{}' "
                                    "observer: {}".format(obs, e))

    def _final_call(self, observer, method, **kwargs):
        if hasattr(observer, method):
            try:
                getattr(observer, method)(**kwargs)
            except Exception:
                # Feels dirty to catch all exceptions, but it is just for
                # finishing up, so we don't want one observer to kill the
                # others
                self.logger.error(traceback.format_exc())

    def _warn_about_failed_observers(self):
        for observer in self._failed_observers:
            self.logger.warning("The observer '{}' failed at some point "
                                "during the run.".format(observer))
