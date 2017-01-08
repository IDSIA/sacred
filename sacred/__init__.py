#!/usr/bin/env python
# coding=utf-8
"""
The main module of sacred.

It provides access to the two main classes Experiment and Ingredient.
"""

from __future__ import division, print_function, unicode_literals

from munch import munchify

SETTINGS = munchify({
    'CONFIG_KEYS': {
        # make sure all config keys are compatible with MongoDB
        'ENFORCE_MONGO_COMPATIBLE': True,
        # make sure all config keys are serializable with jsonpickle
        # THIS IS IMPORTANT. Only deactivate if you know what you're doing.
        'ENFORCE_JSONPICKLE_COMPATIBLE': True,
        # make sure all config keys are valid python identifiers
        'ENFORCE_VALID_PYTHON_IDENTIFIER': False,
        # make sure all config keys are strings
        'ENFORCE_STRING': False
    }})

from .__about__ import __version__, __author__, __author_email__, __url__

from .experiment import Experiment
from .ingredient import Ingredient
from sacred import observers
from sacred.host_info import host_info_getter

__all__ = ('Experiment', 'Ingredient', 'observers', 'host_info_getter',
           '__version__', '__author__', '__author_email__', '__url__',
           'SETTINGS')
