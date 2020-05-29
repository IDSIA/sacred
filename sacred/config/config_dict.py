#!/usr/bin/env python
# coding=utf-8

from sacred.config.config_summary import ConfigSummary
from sacred.config.utils import (
    dogmatize,
    normalize_or_die,
    undogmatize,
    recursive_fill_in,
)


class ConfigDict:
    def __init__(self, d):
        self._conf = normalize_or_die(d)

    def __call__(self, fixed=None, preset=None, fallback=None):
        result = dogmatize(fixed or {})
        recursive_fill_in(result, self._conf)
        recursive_fill_in(result, preset or {})
        added = result.revelation()
        config_summary = ConfigSummary(added, result.modified, result.typechanges)
        config_summary.update(undogmatize(result))
        return config_summary
