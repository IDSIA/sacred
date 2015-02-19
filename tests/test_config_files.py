#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import tempfile
import pytest
from sacred.config_files import (HANDLER_BY_EXT, load_config_file)

data = {
    'foo': 42,
    'baz': [1, 0.2, 'bar', True, {
        'some_number': -12,
        'simon': 'hugo'
    }]
}


@pytest.mark.parametrize('handler', HANDLER_BY_EXT.values())
def test_save_and_load(handler):
    with tempfile.TemporaryFile('w+' + handler.mode) as f:
        handler.dump(data, f)
        f.seek(0)  # simulates closing and reopening
        d = handler.load(f)
        assert d == data


@pytest.mark.parametrize('ext, handler', HANDLER_BY_EXT.items())
def test_load_config_file(ext, handler):
    with tempfile.NamedTemporaryFile('w+' + handler.mode, suffix=ext) as f:
        handler.dump(data, f)
        f.seek(0)
        d = load_config_file(f.name)
        assert d == data