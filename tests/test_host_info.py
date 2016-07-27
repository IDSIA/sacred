#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import sacred.host_info as hi
from sacred.host_info import get_host_info, host_info
from past.builtins import basestring


def test_get_host_info():
    host_info = get_host_info()
    assert isinstance(host_info['hostname'], basestring)
    assert isinstance(host_info['cpu'], basestring)
    assert isinstance(host_info['os'], (tuple, list))
    assert isinstance(host_info['python_version'], basestring)


def test_host_info_decorator():
    try:
        assert 'greeting' not in hi.host_info_gatherers

        @host_info
        def greeting():
            return "hello"

        assert 'greeting' in hi.host_info_gatherers
        assert hi.host_info_gatherers['greeting'] == greeting
        assert get_host_info()['greeting'] == 'hello'
    finally:
        del hi.host_info_gatherers['greeting']


def test_host_info_decorator_with_name():
    try:
        assert 'foo' not in hi.host_info_gatherers

        @host_info(name='foo')
        def greeting():
            return "hello"

        assert 'foo' in hi.host_info_gatherers
        assert 'greeting' not in hi.host_info_gatherers
        assert hi.host_info_gatherers['foo'] == greeting
        assert get_host_info()['foo'] == 'hello'
    finally:
        del hi.host_info_gatherers['foo']
