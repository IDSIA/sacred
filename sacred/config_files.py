#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import os


def json_loader(filename):
    import json
    with open(filename, 'r') as f:
        return json.load(f)


def pickle_loader(filename):
    import pickle
    with open(filename, 'r') as f:
        return pickle.load(f)


def yaml_loader(filename):
    try:
        import yaml
    except ImportError:
        raise ImportError('Failed to import PyYAML.')

    with open(filename, 'r') as f:
        return yaml.load(f)


LOADER_BY_EXT = {
    'json': json_loader,
    'pickle': pickle_loader,
    'yaml': yaml_loader
}


def load_config_file(filename):
    _, extension = os.path.splitext(filename)
    return LOADER_BY_EXT[extension](filename)
