#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import json
import os
import pickle

import sacred.optional as opt

__sacred__ = True  # marks files that should be filtered from stack traces


class Handler(object):
    def __init__(self, load, dump, mode):
        self.load = load
        self.dump = dump
        self.mode = mode

HANDLER_BY_EXT = {
    '.json': Handler(json.load, json.dump, ''),
    '.pickle': Handler(pickle.load, pickle.dump, 'b'),
}


if opt.has_yaml:
    HANDLER_BY_EXT['.yaml'] = Handler(opt.yaml.load, opt.yaml.dump, '')


def load_config_file(filename):
    _, extension = os.path.splitext(filename)
    handler = HANDLER_BY_EXT[extension]
    with open(filename, 'r' + handler.mode) as f:
        return handler.load(f)
