#!/usr/bin/env python
# coding=utf-8

import os
import pickle

import json

import sacred.optional as opt
from sacred.serializer import flatten, restore

__all__ = ("load_config_file", "save_config_file")


class Handler:
    def __init__(self, load, dump, mode):
        self.load = load
        self.dump = dump
        self.mode = mode


HANDLER_BY_EXT = {
    ".json": Handler(
        lambda fp: restore(json.load(fp)),
        lambda obj, fp: json.dump(flatten(obj), fp, sort_keys=True, indent=2),
        "",
    ),
    ".pickle": Handler(pickle.load, pickle.dump, "b"),
}

yaml_extensions = (".yaml", ".yml")
if opt.has_yaml:

    def load_yaml(filename):
        return opt.yaml.load(filename, Loader=opt.yaml.FullLoader)

    yaml_handler = Handler(load_yaml, opt.yaml.dump, "")

    for extension in yaml_extensions:
        HANDLER_BY_EXT[extension] = yaml_handler


def get_handler(filename):
    _, extension = os.path.splitext(filename)
    if extension in yaml_extensions and not opt.has_yaml:
        raise KeyError(
            'Configuration file "{}" cannot be loaded as '
            "you do not have PyYAML installed.".format(filename)
        )
    try:
        return HANDLER_BY_EXT[extension]
    except KeyError:
        raise ValueError(
            'Configuration file "{}" has invalid or unsupported extension '
            '"{}".'.format(filename, extension)
        )


def load_config_file(filename):
    handler = get_handler(filename)
    with open(filename, "r" + handler.mode) as f:
        return handler.load(f)


def save_config_file(config, filename):
    handler = get_handler(filename)
    with open(filename, "w" + handler.mode) as f:
        handler.dump(config, f)
