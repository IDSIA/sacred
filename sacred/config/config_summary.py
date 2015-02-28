#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals


class ConfigSummary(dict):
    def __init__(self):
        super(ConfigSummary, self).__init__()
        self.added_values = set()
        self.ignored_fallback_writes = []  # TODO: test for this member
        self.modified = set()  # TODO: test for this member
        self.typechanges = {}
