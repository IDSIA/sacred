#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from sacred.config.config_summary import ConfigSummary
from sacred.config.utils import dogmatize, normalize_or_die, undogmatize


class ConfigDict(object):
    def __init__(self, d):
        super(ConfigDict, self).__init__()
        self._conf = normalize_or_die(d)

    def __call__(self, fixed=None, preset=None, fallback=None):
        result = dogmatize(fixed or {})
        result.update(preset)
        result.update(self._conf)
        added = result.revelation()
        config_summary = ConfigSummary(added, result.modified,
                                       result.typechanges)
        config_summary.update(undogmatize(result))
        return config_summary
