#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import importlib
from sacred.utils import modules_exist


class MissingDependencyMock(object):
    def __init__(self, depends_on):
        self.depends_on = depends_on

    def __getattribute__(self, item):
        dep = object.__getattribute__(self, 'depends_on')
        if isinstance(dep, (list, tuple)):
            raise ImportError('Depends on missing {!r} packages.'.format(dep))
        else:
            raise ImportError('Depends on missing {!r} package.'.format(dep))

    def __call__(self, *args, **kwargs):
        dep = object.__getattribute__(self, 'depends_on')
        if isinstance(dep, (list, tuple)):
            raise ImportError('Depends on missing {!r} packages.'.format(dep))
        else:
            raise ImportError('Depends on missing {!r} package.'.format(dep))


def optional_import(*package_names):
    try:
        packages = [importlib.import_module(pn) for pn in package_names]
        return True, packages[0]
    except ImportError:
        return False, None


# Get libc in a cross-platform way and use it to also flush the c stdio buffers
# credit to J.F. Sebastians SO answer from here:
# http://stackoverflow.com/a/22434262/1388435
try:
    import ctypes
    from ctypes.util import find_library
except ImportError:
    has_libc, libc = False, None
else:
    try:
        has_libc, libc = True, ctypes.cdll.msvcrt  # Windows
    except OSError:
        has_libc, libc = True, ctypes.cdll.LoadLibrary(find_library('c'))


has_numpy, np = optional_import('numpy')
has_yaml, yaml = optional_import('yaml')
has_pandas, pandas = optional_import('pandas')

has_sqlalchemy = modules_exist('sqlalchemy')
has_mako = modules_exist('mako')
has_gitpython = modules_exist('git')
has_tinydb = modules_exist('tinydb', 'tinydb_serialization', 'hashfs')
has_requests = modules_exist('requests')
has_tensorflow = modules_exist("tensorflow")
has_telegram = modules_exist('telegram')
