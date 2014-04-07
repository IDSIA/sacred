#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from datetime import timedelta
import inspect
import os.path
import time
from sperment.arg_parser import parse_arguments
from sperment.captured_function import CapturedFunction
from sperment.config_scope import ConfigScope
from sperment.utils import create_basic_stream_logger


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
        self.cfgs.append(ConfigScope(f))
        return self.cfgs[-1]

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

    def automain(self, f):
        captured = self.main(f)
        if f.__module__ == '__main__':
            self.run()
        return captured

    ############################## public interface ############################
    def run(self, use_args=True):
        config_updates = {}
        if use_args:
            config_updates, observers = parse_arguments()
            for obs in observers:
                self.add_observer(obs)

        if self.cfgs:
            assert self.cfg is None
            current_cfg = {}
            for c in self.cfgs:
                c.execute(config_updates, preset=current_cfg)
                current_cfg.update(c)
            self.cfg = current_cfg

        self._set_up_logging()

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
        self.logger.info("Experiment started.")
        self.description['start_time'] = time.time()
        for o in self._observers:
            try:
                o.experiment_started_event(
                    name=self.description['name'],
                    mainfile=self.description['mainfile'],
                    doc=self.description['doc'],
                    start_time=self.description['start_time'],
                    config=self.cfg,
                    info=self.description['info'])
            except AttributeError:
                pass

    def _emit_info_updated(self):
        for o in self._observers:
            try:
                o.experiment_info_updated(info=self.description['info'])
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
                o.experiment_completed_event(stop_time=stop_time,
                                             result=result,
                                             info=self.description['info'])
            except AttributeError:
                pass

    def _emit_interrupted(self):
        self.logger.warning("Experiment aborted!")
        interrupt_time = self._stop_time()
        for o in self._observers:
            try:
                o.experiment_interrupted_event(interrupt_time=interrupt_time,
                                               info=self.description['info'])
            except AttributeError:
                pass

    def _emit_failed(self):
        self.logger.warning("Experiment failed!")
        fail_time = self._stop_time()
        for o in self._observers:
            try:
                o.experiment_failed_event(fail_time=fail_time,
                                          info=self.description['info'])
            except AttributeError:
                pass

    def _set_up_logging(self):
        if self.logger is None:
            self.logger = create_basic_stream_logger(self.description['name'])
            self.logger.debug("No logger given. Created basic stream logger.")
        for cf in self._captured_functions:
            cf.logger = self.logger.getChild(cf.__name__)