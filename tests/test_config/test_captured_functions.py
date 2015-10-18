#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import datetime
import mock
import random
from sacred.config.captured_function import create_captured_function


def test_create_captured_function():
    def foo():
        """my docstring"""
        return 42

    cf = create_captured_function(foo)

    assert cf.__name__ == 'foo'
    assert cf.__doc__ == 'my docstring'
    assert cf.prefix is None
    assert cf.config == {}
    assert not cf.uses_randomness
    assert callable(cf)


def test_call_captured_function():
    def foo(a, b, c, d=4, e=5, f=6):
        return a, b, c, d, e, f

    cf = create_captured_function(foo)
    cf.logger = mock.MagicMock()
    cf.config = {'a': 11, 'b': 12, 'd': 14}

    assert cf(21, c=23, f=26) == (21, 12, 23, 14, 5, 26)
    cf.logger.debug.assert_has_calls([
        mock.call("Started"),
        mock.call("Finished after %s.", datetime.timedelta(0))])


def test_captured_function_randomness():
    def foo(_rnd, _seed):
        return _rnd.randint(0, 1000), _seed

    cf = create_captured_function(foo)
    assert cf.uses_randomness
    cf.logger = mock.MagicMock()
    cf.rnd = random.Random(1234)

    nr1, seed1 = cf()
    nr2, seed2 = cf()
    assert nr1 != nr2
    assert seed1 != seed2

    cf.rnd = random.Random(1234)

    assert cf() == (nr1, seed1)
    assert cf() == (nr2, seed2)


def test_captured_function_magic_logger_argument():
    def foo(_log):
        return _log

    cf = create_captured_function(foo)
    cf.logger = mock.MagicMock()

    assert cf() == cf.logger


def test_captured_function_magic_config_argument():
    def foo(_config):
        return _config

    cf = create_captured_function(foo)
    cf.logger = mock.MagicMock()
    cf.config = {'a': 2, 'b': 2}

    assert cf() == cf.config


def test_captured_function_magic_run_argument():
    def foo(_run):
        return _run

    cf = create_captured_function(foo)
    cf.logger = mock.MagicMock()
    cf.run = mock.MagicMock()

    assert cf() == cf.run
