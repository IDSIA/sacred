#!/usr/bin/env python
# coding=utf-8


import os
import re
import tempfile
import pytest

from sacred.config.config_files import HANDLER_BY_EXT, load_config_file

data = {"foo": 42, "baz": [1, 0.2, "bar", True, {"some_number": -12, "simon": "hugo"}]}


@pytest.mark.parametrize("handler", HANDLER_BY_EXT.values())
def test_save_and_load(handler):
    with tempfile.TemporaryFile("w+" + handler.mode) as f:
        handler.dump(data, f)
        f.seek(0)  # simulates closing and reopening
        d = handler.load(f)
        assert d == data


@pytest.mark.parametrize("ext, handler", HANDLER_BY_EXT.items())
def test_load_config_file(ext, handler):
    handle, f_name = tempfile.mkstemp(suffix=ext)
    f = os.fdopen(handle, "w" + handler.mode)
    handler.dump(data, f)
    f.close()
    d = load_config_file(f_name)
    assert d == data
    os.remove(f_name)


def test_load_config_file_exception_msg_invalid_ext():
    handle, f_name = tempfile.mkstemp(suffix=".invalid")
    f = os.fdopen(handle, "w")  # necessary for windows
    f.close()
    try:
        exception_msg = re.compile(
            'Configuration file ".*.invalid" has invalid or '
            'unsupported extension ".invalid".'
        )
        with pytest.raises(ValueError) as excinfo:
            load_config_file(f_name)
        assert exception_msg.match(excinfo.value.args[0])
    finally:
        os.remove(f_name)
