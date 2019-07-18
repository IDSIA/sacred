#!/usr/bin/env python
# coding=utf-8

import importlib
from sacred.utils import modules_exist


def optional_import(*package_names):
    try:
        packages = [importlib.import_module(pn) for pn in package_names]
        return True, packages[0]
    except ImportError:
        return False, None


has_numpy, np = optional_import('numpy')
has_yaml, yaml = optional_import('yaml')
has_pandas, pandas = optional_import('pandas')

has_sqlalchemy = modules_exist('sqlalchemy')
has_mako = modules_exist('mako')
has_gitpython = modules_exist('git')
has_tinydb = modules_exist('tinydb', 'tinydb_serialization', 'hashfs')
has_tensorflow = modules_exist("tensorflow")
