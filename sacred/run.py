#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from copy import copy
from datetime import timedelta
import sys
import threading
import time
import traceback

from sacred.config_scope import dogmatize, undogmatize
from sacred.utils import (
    create_rnd, create_basic_stream_logger, get_seed, iterate_flattened,
    iter_path_splits, iter_prefixes, join_paths, set_by_dotted_path,
    tee_output, is_prefix)


class Status(object):
    SET_UP = 0
    STARTING = 1
    RUNNING = 2
    COMPLETED = 3
    INTERRUPTED = 4
    FAILED = 5


class ModuleRunner(object):
    def __init__(self, config_scopes, subrunners, path, captured_functions,
                 generate_seed):
        self.config_scopes = config_scopes
        self.subrunners = subrunners
        self.path = path
        self.generate_seed = generate_seed
        self.config_updates = {}
        self.config = None
        self.fixture = None  # TODO: rename
        self.logger = None
        self.seed = None
        self.rnd = None
        self._captured_functions = captured_functions

    def set_up_logging(self, parent_logger, as_name=None):
        if self.logger is not None:
            return
        as_name = self.path if as_name is None else as_name
        self.logger = parent_logger.getChild(as_name)
        self.logger.debug("No logger given. Created basic stream logger.")

    def set_up_seed(self, rnd=None):
        if self.seed is not None:
            return

        self.seed = self.config_updates.get('seed') or get_seed(rnd)
        self.rnd = create_rnd(self.seed)

        # Hierarchically set the seed of proper subrunners
        for subrunner in reversed(self.subrunners):
            if is_prefix(self.path, subrunner.path):
                subrunner.set_up_seed(self.rnd)

    def set_up_config(self):
        if self.config is not None:
            return self.config

        # gather presets
        fallback = {}
        for sr in self.subrunners:
            if self.path and is_prefix(self.path, sr.path):
                path = sr.path[len(self.path):].strip('.')
                set_by_dotted_path(fallback, path, sr.config)
            else:
                set_by_dotted_path(fallback, sr.path, sr.config)

        # dogmatize to make the subrunner configurations read-only
        const_fallback = dogmatize(fallback)
        const_fallback.revelation()

        self.config = {}

        if self.generate_seed:
            self.config['seed'] = self.seed

        for config in self.config_scopes:
            config(fixed=self.config_updates,
                   preset=self.config,
                   fallback=const_fallback)
            self.config.update(config)

        self.config = undogmatize(self.config)

        return self.config

    def get_config_modifications(self):
        added = set()
        typechanges = {}
        flat_config_upd = [k for k, v in iterate_flattened(self.config_updates)]
        updated = {sp for p in flat_config_upd for sp in iter_prefixes(p)}
        for config in self.config_scopes:
            added |= config.added_values
            typechanges.update(config.typechanges)

        return added, updated, typechanges

    def get_fixture(self):
        if self.fixture is not None:
            return self.fixture

        self.fixture = copy(self.config)
        for sr in self.subrunners:
            sub_fix = sr.get_fixture()
            sub_path = sr.path
            if is_prefix(self.path, sub_path):
                sub_path = sr.path[len(self.path):].strip('.')
            # Note: This might fail if we allow non-dict fixtures
            set_by_dotted_path(self.fixture, sub_path, sub_fix)
        return self.fixture

    def finalize_initialization(self, run):
        # look at seed again, because it might have changed during the
        # configuration process
        if 'seed' in self.config:
            self.seed = self.config['seed']
            self.rnd = create_rnd(self.seed)

        for cf in self._captured_functions:
            cf.logger = self.logger.getChild(cf.__name__)
            cf.config = self.get_fixture()
            cf.seed = get_seed(self.rnd)
            cf.rnd = create_rnd(cf.seed)
            cf.run = run

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
    Represents and manages a single run of an experiment.
    """

    def __init__(self, name, modrunners, main_function, observers):
        self.exname = name
        self.modrunners = modrunners
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
        self.logger = None

    def initialize_logging(self, loglevel=None):
        if loglevel:
            try:
                loglevel = int(loglevel)
            except ValueError:
                pass
        root_logger = create_basic_stream_logger('', level=loglevel)
        for mr in self.modrunners:
            mr.set_up_logging(root_logger)
        self.logger = root_logger.getChild(self.exname)

    def distribute_config_updates(self, config_updates):
        modrunner_cfgups = {m.path: m.config_updates for m in self.modrunners}
        for path, value in iterate_flattened(config_updates):
            for p1, p2 in reversed(list(iter_path_splits(path))):
                if p1 in modrunner_cfgups:
                    set_by_dotted_path(modrunner_cfgups[p1], p2, value)
                    break
                    # this is guaranteed to occur for one of the modrunners,
                    # because the exrunner has path ''

    def initialize(self, config_updates=None, loglevel=None):
        self.initialize_logging(loglevel)

        if config_updates is not None:
            self.distribute_config_updates(config_updates)

        for mr in reversed(self.modrunners):
            mr.set_up_seed()  # partially recursive

        for mr in self.modrunners:
            mr.set_up_config()

        for mr in self.modrunners:
            mr.finalize_initialization(run=self)

        self.status = Status.STARTING

    def get_configuration(self):
        config = {}
        for mr in reversed(self.modrunners):
            if mr.path:
                set_by_dotted_path(config, mr.path, mr.config)
            else:
                config.update(mr.config)

        return config

    def get_config_modifications(self):
        added = set()
        updated = set()
        typechanges = {}
        for mr in self.modrunners:
            mr_add, mr_up, mr_tc = mr.get_config_modifications()
            if mr_add or mr_up or mr_tc:
                updated |= set(iter_prefixes(mr.path))
            added |= {join_paths(mr.path, a) for a in mr_add}
            updated |= {join_paths(mr.path, u) for u in mr_up}
            typechanges.update({join_paths(mr.path, k): v
                                for k, v in mr_tc.items()})

        return added, updated, typechanges

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
        self.start_time = time.time()
        for o in self._observers:
            try:
                o.started_event(
                    start_time=self.start_time,
                    config=self.get_configuration())
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
        return self.stop_time

    def _emit_completed(self, result):
        stop_time = self._stop_time()
        for o in self._observers:
            try:
                o.completed_event(
                    stop_time=stop_time,
                    result=result)
            except AttributeError:
                pass

    def _emit_interrupted(self):
        self.logger.warning("Aborted!")
        interrupt_time = self._stop_time()
        for o in self._observers:
            try:
                o.interrupted_event(
                    interrupt_time=interrupt_time)
            except AttributeError:
                pass

    def _emit_failed(self, etype, value, tb):
        self.logger.warning("Failed!")
        fail_time = self._stop_time()
        fail_trace = traceback.format_exception(etype, value, tb)
        for o in self._observers:
            try:
                o.failed_event(
                    fail_time=fail_time,
                    fail_trace=fail_trace)
            except:  # _emit_failed should never throw
                pass
