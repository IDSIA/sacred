#!/usr/bin/env python
# coding=utf-8

import pytest

from sacred.host_info import get_host_info, host_info_getter, host_info_gatherers


def test_get_host_info():
    host_info = get_host_info()
    assert isinstance(host_info["hostname"], str)
    assert isinstance(host_info["cpu"], str)
    assert isinstance(host_info["os"], (tuple, list))
    assert isinstance(host_info["python_version"], str)


def test_host_info_decorator():
    try:
        assert "greeting" not in host_info_gatherers

        @host_info_getter
        def greeting():
            return "hello"

        assert "greeting" in host_info_gatherers
        assert host_info_gatherers["greeting"] == greeting
        assert get_host_info()["greeting"] == "hello"
    finally:
        del host_info_gatherers["greeting"]


def test_host_info_decorator_with_name():
    try:
        assert "foo" not in host_info_gatherers

        @host_info_getter(name="foo")
        def greeting():
            return "hello"

        assert "foo" in host_info_gatherers
        assert "greeting" not in host_info_gatherers
        assert host_info_gatherers["foo"] == greeting
        assert get_host_info()["foo"] == "hello"
    finally:
        del host_info_gatherers["foo"]


def test_host_info_decorator_depreciation_warning():
    try:
        assert "foo" not in host_info_gatherers

        with pytest.warns(DeprecationWarning):

            @host_info_getter(name="foo")
            def greeting():
                return "hello"

    finally:
        del host_info_gatherers["foo"]
