#!/usr/bin/env python
# coding=utf-8

import importlib
from sacred.utils import modules_exist
from sacred.utils import get_package_version, parse_version


def optional_import(*package_names):
    try:
        packages = [importlib.import_module(pn) for pn in package_names]
        return True, packages[0]
    except ImportError:
        return False, None


def get_tensorflow(allow_mock=False):
    # Ensures backward and forward compatibility with TensorFlow 1 and 2.
    if has_tensorflow:
        if get_package_version('tensorflow') < parse_version('1.13.1'):
            import warnings
            warnings.warn("Use of TensorFlow 1.12 and older is deprecated. "
                          "Use Tensorflow 1.13 or newer instead.",
                          DeprecationWarning)
            import tensorflow
        else:
            import tensorflow.compat.v1 as tensorflow
    else:
        # Let's define a mocked tensorflow
        class tensorflow:
            class summary:
                class FileWriter:
                    def __init__(self, logdir, graph):
                        self.logdir = logdir
                        self.graph = graph
                        print("Mocked FileWriter got logdir=%s, graph=%s" % (logdir, graph))

            class Session:
                def __init__(self):
                    self.graph = None

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass
    return tensorflow


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
has_tensorflow = modules_exist("tensorflow")
