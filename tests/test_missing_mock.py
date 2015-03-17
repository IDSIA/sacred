#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import pytest
from sacred.optional import MissingDependencyMock


def test_missing_dependency_mock_raises_on_access():
    MongoObserver = MissingDependencyMock('pymongo')
    with pytest.raises(ImportError) as e:
        MongoObserver.create(db_name='db_name', url='url')
    assert e.value.args[0].find('pymongo') > -1
