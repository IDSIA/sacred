#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import os.path
import mock
import pytest
from sacred.dependencies import (
    PEP440_VERSION_PATTERN, Source, get_py_file_if_possible, PackageDependency)

EXAMPLE_SOURCE = 'tests/__init__.py'
EXAMPLE_DIGEST = \
    'dca1c3c61e6d88a278551deb7110bbacaf5458f11af9818171d72e1af0b55114'


@pytest.mark.parametrize('version', [
    '0.9.11', '2012.04', '1!1.1', '17.10a104', '43.0rc1', '0.9.post3',
    '12.4a22.post8', '13.3rc2.dev1515', '1.0.dev456', '1.0a1', '1.0a2.dev456',
    '1.0a12.dev456', '1.0a12', '1.0b1.dev456', '1.0b2', '1.0b2.post345.dev456',
    '1.0b2.post345', '1.0rc1.dev456', '1.0rc1', '1.0', '1.0.post456.dev34',
    '1.0.post456', '1.1.dev1'
])
def test_pep440_version_pattern(version):
    assert PEP440_VERSION_PATTERN.match(version)


def test_pep440_version_pattern_invalid():
    assert PEP440_VERSION_PATTERN.match('foo') is None
    assert PEP440_VERSION_PATTERN.match('_12_') is None
    assert PEP440_VERSION_PATTERN.match('version 4') is None


def test_source_get_digest():
    assert Source.get_digest(EXAMPLE_SOURCE) == EXAMPLE_DIGEST


def test_source_create_empty():
    with pytest.raises(ValueError):
        Source.create('')


def test_source_create_non_existing():
    with pytest.raises(ValueError):
        Source.create('doesnotexist.py')


def test_source_create_py():
    s = Source.create(EXAMPLE_SOURCE)
    assert s.filename == os.path.abspath(EXAMPLE_SOURCE)
    assert s.digest == EXAMPLE_DIGEST


def test_get_py_file_if_possible_with_py_file():
    assert get_py_file_if_possible(EXAMPLE_SOURCE) == EXAMPLE_SOURCE


def test_get_py_file_if_possible_with_pyc_file():
    assert get_py_file_if_possible(EXAMPLE_SOURCE + 'c') == EXAMPLE_SOURCE


def test_get_py_file_if_possible_with_pyc_but_nonexistent_py_file():
    assert get_py_file_if_possible('doesnotexist.pyc') == 'doesnotexist.pyc'


versions = [
    ('0.7.2', '0.7.2'),
    ('1.0', '1.0'),
    ('foobar', None),
    (10, None),
    ((2, 6), '2.6'),
    ((1, 4, 8), '1.4.8')
]


@pytest.mark.parametrize('version,expected', versions)
def test_package_dependency_get_version_heuristic_version__(version, expected):
    mod = mock.Mock(spec=[], __version__=version)
    assert PackageDependency.get_version_heuristic(mod) == expected


@pytest.mark.parametrize('version,expected', versions)
def test_package_dependency_get_version_heuristic_version(version, expected):
    mod = mock.Mock(spec=[], version=version)
    assert PackageDependency.get_version_heuristic(mod) == expected


@pytest.mark.parametrize('version,expected', versions)
def test_package_dependency_get_version_heuristic_VERSION(version, expected):
    mod = mock.Mock(spec=[], VERSION=version)
    assert PackageDependency.get_version_heuristic(mod) == expected