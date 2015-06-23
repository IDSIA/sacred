#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import pytest
from sacred.optional import MissingDependencyMock, optional_import


def test_missing_dependency_mock_raises_on_access():
    MongoObserver = MissingDependencyMock('pymongo')
    with pytest.raises(ImportError) as e:
        MongoObserver.create(db_name='db_name', url='url')
    assert e.value.args[0].find('pymongo') > -1


def test_missing_dependency_mock_raises_on_call():
    MongoObserver = MissingDependencyMock('pymongo')
    with pytest.raises(ImportError) as e:
        MongoObserver('some', params='passed')
    assert e.value.args[0].find('pymongo') > -1


def test_optional_import():
    has_pytest, pyt = optional_import('pytest')
    assert has_pytest
    assert pyt == pytest


def test_optional_import_nonexisting():
    has_nonex, nonex = optional_import('clearlynonexistingpackage')
    assert not has_nonex
    assert nonex is None
