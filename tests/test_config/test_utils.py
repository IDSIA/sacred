#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import pytest
from sacred import optional as opt
from sacred.config.utils import normalize_or_die


@pytest.mark.skipif(not opt.has_numpy, reason="requires numpy")
@pytest.mark.parametrize('typename', [
    'bool_', 'int_', 'intc', 'intp', 'int8', 'int16', 'int32', 'int64',
    'uint8', 'uint16', 'uint32', 'uint64', 'float_', 'float16', 'float32',
    'float64'])
def test_normalize_or_die_for_numpy_datatypes(typename):
    dtype = getattr(opt.np, typename)
    assert normalize_or_die(dtype(7.))


@pytest.mark.skipif(not opt.has_numpy, reason="requires numpy")
@pytest.mark.parametrize('typename', [
    'bool_', 'int_', 'intc', 'intp', 'int8', 'int16', 'int32', 'int64',
    'uint8', 'uint16', 'uint32', 'uint64', 'float_', 'float16', 'float32',
    'float64'])
def test_normalize_or_die_for_numpy_arrays(typename):
    np = opt.np
    dtype = getattr(np, typename)
    a = np.array([0, 1, 2], dtype=dtype)
    b = normalize_or_die(a)
    assert len(b) == 3
