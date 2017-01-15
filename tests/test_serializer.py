#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import pytest

from sacred.serializer import flatten, restore
import sacred.optional as opt


@pytest.mark.parametrize('obj', [
    12,
    3.14,
    "mystring",
    "αβγδ",
    [1, 2., "3", [4]],
    {'foo': 'bar', 'answer': 42},
    None,
    True
])
def test_flatten_on_json_is_noop(obj):
    assert flatten(obj) == obj


@pytest.mark.parametrize('obj', [
    12,
    3.14,
    "mystring",
    "αβγδ",
    [1, 2., "3", [4]],
    {'foo': 'bar', 'answer': 42},
    None,
    True
])
def test_restore_on_json_is_noop(obj):
    assert flatten(obj) == obj


def test_serialize_non_str_keys():
    d = {1: "one", 2: "two"}
    assert restore(flatten(d)) == d


@pytest.mark.skipif(not opt.has_numpy, reason="requires numpy")
@pytest.mark.parametrize('typename', [
    'bool_', 'int_', 'intc', 'intp', 'int8', 'int16', 'int32', 'int64',
    'uint8', 'uint16', 'uint32', 'uint64', 'float_', 'float16', 'float32',
    'float64'])
def test_flatten_normalizes_numpy_scalars(typename):
    dtype = getattr(opt.np, typename)
    a = 1
    b = flatten(dtype(a))
    assert a == b
    assert isinstance(b, (int, bool, float))


@pytest.mark.skipif(not opt.has_numpy, reason="requires numpy")
def test_serialize_numpy_arrays():
    a = opt.np.array([[1, 2, 3], [4, 5, 6]], dtype=opt.np.float32)
    b = restore(flatten(a))
    assert opt.np.all(b == a)
    assert b.dtype == a.dtype
    assert b.shape == a.shape


def test_serialize_tuples():
    t = (1, 'two')
    assert restore(flatten(t)) == t
    assert isinstance(restore(flatten(t)), tuple)


@pytest.mark.skipif(not opt.has_pandas, reason="requires pandas")
def test_serialize_pandas_dataframes():
    pd, np = opt.pandas, opt.np
    df = pd.DataFrame(np.arange(20).reshape(5, 4), columns=list('ABCD'))
    b = restore(flatten(df))
    assert np.all(df == b)
    assert np.all(df.dtypes == b.dtypes)


# def test_serialize_datetime():
#     from datetime import datetime
#     t = datetime.utcnow()
#     assert restore(flatten(t)) == t


