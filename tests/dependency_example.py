#!/usr/bin/env python
# coding=utf-8
"""
A file for testing the gathering of sources and dependency by test_dependencies
"""
from __future__ import division, print_function, unicode_literals

import mock
import pytest

from tests.foo import bar


# Actually this would not work :(
# import tests.foo.bar


def some_func():
    pass

ignore_this = 17
