#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
import inspect
import os.path
import time
from sperment.captured_function import CapturedFunction
from sperment.config_scope import ConfigScope


class Experiment(object):
    INITIALIZING, RUNNING, COMPLETED, INTERRUPTED, FAILED = range(5)

    def __init__(self, name=None, config=None):
        self.config = config if config is not None else dict()
        self._status = Experiment.INITIALIZING
        self._main_function = None
        self._captured_functions = []
        self._observers = []

        self.description = {
            'name': name,
            'doc': None,
            'mainfile': None,
            'info': {},
            'seed': None,
            'start_time': None,
            'stop_time': None
        }

    ############################## Decorators ##################################

    def config(self, f):
        self.config = ConfigScope(f)
        return self.config

    def capture(self, f):
        captured_function = CapturedFunction(f, self)
        self._captured_functions.append(captured_function)
        return captured_function

    def main(self, f):
        self._main_function = self.capture(f)
        mainfile = inspect.getabsfile(f)
        self.description['mainfile'] = mainfile

        if self.description['name'] is None:
            filename = os.path.basename(mainfile)
            self.description['name'] = filename.rsplit('.', 1)[0]

        self.description['doc'] = inspect.getmodule(f).__doc__

        return self._main_function

    ############################## public interface ############################
    def run(self):
        self._status = Experiment.RUNNING
        self._emit_started()
        try:
            result = self._main_function()
            self._status = Experiment.COMPLETED
            self._emit_completed(result)
            return result
        except KeyboardInterrupt:
            self._status = Experiment.INTERRUPTED
            self._emit_interrupted()
            raise
        except:
            self._status = Experiment.FAILED
            self._emit_failed()
            raise

    ################### Observable interface ###################################
    def add_observer(self, obs):
        if not obs in self._observers:
            self._observers.append(obs)

    def remove_observer(self, obs):
        if obs in self._observers:
            self._observers.remove(obs)

    def _emit_started(self):
        self.description['start_time'] = time.time()
        for o in self._observers:
            try:
                o.experiment_started_event(
                    name=self.description['name'],
                    mainfile=self.description['mainfile'],
                    doc=self.description['doc'],
                    start_time=self.description['start_time'],
                    config=self.config,
                    info=self.description['info'])
            except AttributeError:
                pass

    def _emit_info_updated(self):
        for o in self._observers:
            try:
                o.experiment_info_updated(info=self.description['info'])
            except AttributeError:
                pass

    def _emit_completed(self, result):
        stop_time = time.time()
        self.description['stop_time'] = stop_time
        for o in self._observers:
            try:
                o.experiment_completed_event(stop_time=stop_time,
                                             result=result,
                                             info=self.description['info'])
            except AttributeError:
                pass

    def _emit_failed(self):
        fail_time = time.time()
        self.description['stop_time'] = fail_time
        for o in self._observers:
            try:
                o.experiment_failed_event(fail_time=fail_time,
                                          info=self.description['info'])
            except AttributeError:
                pass

    def _emit_interrupted(self):
        interrupt_time = time.time()
        self.description['stop_time'] = interrupt_time
        for o in self._observers:
            try:
                o.experiment_interrupted_event(interrupt_time=interrupt_time,
                                               info=self.description['info'])
            except AttributeError:
                pass