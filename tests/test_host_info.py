#!/usr/bin/env python
# coding=utf-8

from sacred.host_info import get_host_info


def test_get_host_info():
    host_info = get_host_info()
    assert isinstance(host_info['hostname'], str)
    assert isinstance(host_info['cpu'], str)
    assert isinstance(host_info['os'], (tuple, list))
    assert isinstance(host_info['python_version'], str)
