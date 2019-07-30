#!/usr/bin/env python
# coding=utf-8

import pytest
from sacred.optional import optional_import, get_tensorflow, modules_exist


def test_optional_import():
    has_pytest, pyt = optional_import("pytest")
    assert has_pytest
    assert pyt == pytest


def test_optional_import_nonexisting():
    has_nonex, nonex = optional_import("clearlynonexistingpackage")
    assert not has_nonex
    assert nonex is None


def test_get_tensorflow():
    """Test that get_tensorflow() runs without error."""
    pytest.importorskip("tensorflow")
    get_tensorflow()


def test_module_exists_for_tensorflow():
    """Check that module_exist returns true if tf is there."""
    pytest.importorskip("tensorflow")
    assert modules_exist("tensorflow")
