#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from sacred.config.path import Path
from sacred.config.path_containers import PathDict, ConfigEntry
from sacred.sentinels import NotSet


class Stage(object):
    def __init__(self, name, parent_config, fixate, mark_as_default):
        self.name = name
        self.parent_config = parent_config
        self.fixate = fixate
        self.mark_as_default = mark_as_default
        self.recorded_changes = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # TODO: handle exceptions?
        self.parent_config.active_stage = None
        if self.fixate:
            for path in self.recorded_changes:
                entry = self.parent_config.cfg.get_entry(path)
                entry.fixed = True

    def make_entry(self, value):
        entry = ConfigEntry(value)
        if self.mark_as_default:
            entry.default = value
        return entry

    def record(self, path):
        self.recorded_changes.append(path)


class Configuration(object):
    def __init__(self, settings=None, logger=None):
        self.settings = settings or {}
        self.log = logger
        self.cfg = PathDict()  # todo: make path dict
        self.stages = []
        self.active_stage = None

    def set(self, k, value):
        path = Path.from_any(k)
        entry = self.active_stage.make_entry(value)
        self.active_stage.record(path)
        self.cfg.update_entry(path, entry)

    def stage(self, name, fixate=True, mark_as_default=False):
        stage = Stage(name, self, fixate, mark_as_default)
        self.stages.append(stage)
        self.active_stage = stage
        return stage

    def finalize(self):
        pass


