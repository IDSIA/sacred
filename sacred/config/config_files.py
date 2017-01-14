#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import os
import pickle

import json

import sacred.optional as opt
from sacred.serializer import flatten, restore

__sacred__ = True  # marks files that should be filtered from stack traces

__all__ = ('load_config_file', 'save_config_file')


class Handler(object):
    def __init__(self, load, dump, mode):
        self.load = load
        self.dump = dump
        self.mode = mode


HANDLER_BY_EXT = {
    '.json': Handler(lambda fp: restore(json.load(fp)),
                     lambda obj, fp: json.dump(flatten(obj), fp,
                                               sort_keys=True, indent=2), ''),
    '.pickle': Handler(pickle.load, pickle.dump, 'b'),
}


if opt.has_yaml:
    HANDLER_BY_EXT['.yaml'] = Handler(opt.yaml.load, opt.yaml.dump, '')


def get_handler(filename):
    _, extension = os.path.splitext(filename)
    return HANDLER_BY_EXT[extension]


def load_config_file(filename):
    handler = get_handler(filename)
    with open(filename, 'r' + handler.mode) as f:
        return handler.load(f)


def save_config_file(config, filename):
    handler = get_handler(filename)
    with open(filename, 'w' + handler.mode) as f:
        handler.dump(config, f)
