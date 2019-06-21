#!/usr/bin/env python
# coding=utf-8

import pytest
from sacred.optional import optional_import


def test_optional_import():
    has_pytest, pyt = optional_import('pytest')
    assert has_pytest
    assert pyt == pytest


def test_optional_import_nonexisting():
    has_nonex, nonex = optional_import('clearlynonexistingpackage')
    assert not has_nonex
    assert nonex is None
