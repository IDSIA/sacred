#!/usr/bin/env python
# coding=utf-8
"""
A file for testing the gathering of sources and dependency by test_dependencies
"""

import mock
import pytest

from tests.foo import bar, mock_extension


# Actually this would not work :(
# import tests.foo.bar


def some_func():
    pass


ignore_this = 17
