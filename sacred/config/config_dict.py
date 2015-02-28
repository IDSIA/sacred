#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from sacred.config.config_summary import ConfigSummary
from sacred.config.utils import normalize_or_die, dogmatize, undogmatize


class ConfigDict(object):
    def __init__(self, d):
        super(ConfigDict, self).__init__()
        self._conf = normalize_or_die(d)

    def __call__(self, fixed=None, preset=None, fallback=None):
        result = dogmatize(fixed or {})
        result.update(preset)
        result.update(self._conf)

        config_summary = ConfigSummary()
        config_summary.added_values = result.revelation()
        config_summary.ignored_fallback_writes = []
        config_summary.modified = result.modified
        config_summary.typechanges = result.typechanges
        config_summary.update(undogmatize(result))

        return config_summary
