#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from sacred import Ingredient, Experiment
from sacred.utils import CircularDependencyError, ConfigAddedError, \
    MissingConfigError, NamedConfigNotFoundError

"""Global Docstring"""

import pytest


def test_circular_dependency_raises():
    # create experiment with circular dependency
    ing = Ingredient('ing')
    ex = Experiment('exp', ingredients=[ing])
    ex.main(lambda: None)
    ing.ingredients.append(ex)

    # run and see if it raises
    with pytest.raises(CircularDependencyError, match='exp->ing->exp'):
        ex.run()


def test_config_added_raises():
    ex = Experiment('exp')
    ex.main(lambda: None)

    with pytest.raises(
            ConfigAddedError,
            match=r'Added new config entry that is not used anywhere.*\n'
                  r'\s*Conflicting configuration values:\n'
                  r'\s*a=42'):
        ex.run(config_updates={'a': 42})


def test_missing_config_raises():
    ex = Experiment('exp')
    ex.main(lambda a: None)
    with pytest.raises(MissingConfigError):
        ex.run()


def test_named_config_not_found_raises():
    ex = Experiment('exp')
    ex.main(lambda: None)
    with pytest.raises(NamedConfigNotFoundError,
                       match='Named config not found: "not_there". '
                             'Available are:'):
        ex.run(named_configs=('not_there',))
