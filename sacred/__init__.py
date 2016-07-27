#!/usr/bin/env python
# coding=utf-8
"""
The main module of sacred.

It provides access to the two main classes Experiment and Ingredient.
"""

from __future__ import division, print_function, unicode_literals

from .__about__ import __version__, __author__, __author_email__, __url__

from .experiment import Experiment
from .ingredient import Ingredient
from sacred import observers
from sacred.host_info import host_info

__all__ = ('Experiment', 'Ingredient', 'observers', 'host_info', '__version__',
           '__author__', '__author_email__', '__url__')
