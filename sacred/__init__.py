#!/usr/bin/env python
# coding=utf-8
"""
The main module of sacred.

It provides access to the two main classes Experiment and Ingredient.
"""

from sacred.__about__ import __version__, __author__, __author_email__, __url__
from sacred.settings import SETTINGS
from sacred.experiment import Experiment
from sacred.ingredient import Ingredient
from sacred import observers


__all__ = ('Experiment', 'Ingredient', 'observers',
           '__version__', '__author__', '__author_email__', '__url__',
           'SETTINGS')
