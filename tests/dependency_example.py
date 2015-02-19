#!/usr/bin/env python
# coding=utf-8
"""
A file for testing the gathering of sources and dependency by test_dependencies
"""
from __future__ import division, print_function, unicode_literals
import pytest
import mock

from tests.foo import bar

# Actually this would not work :(
# import tests.foo.bar


def some_func(): pass
