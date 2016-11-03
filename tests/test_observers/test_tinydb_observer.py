#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import datetime

import os

import mock
# import mongomock
import pytest
import tempfile

from tinydb import TinyDB, Query

from hashfs import HashFS

from sacred.dependencies import get_digest
from sacred.observers.tinydb import TinyDbObserver
from sacred import optional as opt

T1 = datetime.datetime(1999, 5, 4, 3, 2, 1, 0)
T2 = datetime.datetime(1999, 5, 5, 5, 5, 5, 5)


@pytest.fixture()
def tinydb_obs(tmpdir):
    return TinyDbObserver.create(path=tmpdir.strpath, name='testdb')


@pytest.fixture()
def sample_run():
    exp = {'name': 'test_exp', 'sources': [], 'doc': '', 'base_dir': '/tmp'}
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}
    config = {'config': 'True', 'foo': 'bar', 'answer': 42}
    command = 'run'
    meta_info = {'comment': 'test run'}
    return {
        '_id': 'FEDCBA9876543210',
        'ex_info': exp,
        'command': command,
        'host_info': host,
        'start_time': T1,
        'config': config,
        'meta_info': meta_info,
    }


def test_tindb_observer_started_event_creates_run(tinydb_obs, sample_run):
    sample_run['_id'] = None
    _id = tinydb_obs.started_event(**sample_run)
    assert _id is not None
    assert len(tinydb_obs.runs) == 1
    db_run = tinydb_obs.runs.get(eid=1)
    assert db_run == {
        '_id': _id,
        'experiment': sample_run['ex_info'],
        'format': tinydb_obs.VERSION,
        'command': sample_run['command'],
        'host': sample_run['host_info'],
        'start_time': sample_run['start_time'],
        'heartbeat': None,
        'info': {},
        'captured_out': '',
        'artifacts': [],
        'config': sample_run['config'],
        'meta': sample_run['meta_info'],
        'status': 'RUNNING',
        'resources': []
    }


def test_tinydb_observer_started_event_uses_given_id(tinydb_obs, sample_run):
    _id = tinydb_obs.started_event(**sample_run)
    assert _id == sample_run['_id']
    assert len(tinydb_obs.runs) == 1
    db_run = tinydb_obs.runs.get(eid=1)
    assert db_run['_id'] == sample_run['_id']


def test_tinydb_observer_equality(tmpdir, tinydb_obs):

    db = TinyDB(os.path.join(tmpdir.strpath, 'metadata.json'))
    fs = HashFS(os.path.join(tmpdir.strpath, 'hashfs'), depth=3, width=2, algorithm='md5')
    m = TinyDbObserver(db, fs)

    assert tinydb_obs == m
    assert not tinydb_obs != m

    assert not tinydb_obs == 'foo'
    assert tinydb_obs != 'foo'


def test_tinydb_observer_heartbeat_event_updates_run(tinydb_obs, sample_run):
    tinydb_obs.started_event(**sample_run)

    info = {'my_info': [1, 2, 3], 'nr': 7}
    outp = 'some output'
    with tempfile.NamedTemporaryFile() as f:
        f.write(outp.encode())
        f.flush()
        tinydb_obs.heartbeat_event(info=info, cout_filename=f.name,
                                   beat_time=T2)

    assert len(tinydb_obs.runs) == 1
    db_run = tinydb_obs.runs.get(eid=1)
    assert db_run['heartbeat'] == T2
    assert db_run['info'] == info
    assert db_run['captured_out'] == outp


def test_tinydb_observer_completed_event_updates_run(tinydb_obs, sample_run):
    tinydb_obs.started_event(**sample_run)

    tinydb_obs.completed_event(stop_time=T2, result=42)

    assert len(tinydb_obs.runs) == 1
    db_run = tinydb_obs.runs.get(eid=1)
    assert db_run['stop_time'] == T2
    assert db_run['result'] == 42
    assert db_run['status'] == 'COMPLETED'


def test_tinydb_observer_interrupted_event_updates_run(tinydb_obs, sample_run):
    tinydb_obs.started_event(**sample_run)

    tinydb_obs.interrupted_event(interrupt_time=T2, status='INTERRUPTED')

    assert len(tinydb_obs.runs) == 1
    db_run = tinydb_obs.runs.get(eid=1)
    assert db_run['stop_time'] == T2
    assert db_run['status'] == 'INTERRUPTED'


def test_tinydb_observer_failed_event_updates_run(tinydb_obs, sample_run):
    tinydb_obs.started_event(**sample_run)

    fail_trace = "lots of errors and\nso\non..."
    tinydb_obs.failed_event(fail_time=T2,
                            fail_trace=fail_trace)

    assert len(tinydb_obs.runs) == 1
    db_run = tinydb_obs.runs.get(eid=1)
    assert db_run['stop_time'] == T2
    assert db_run['status'] == 'FAILED'
    assert db_run['fail_trace'] == fail_trace


def test_tinydb_observer_artifact_event(tinydb_obs, sample_run):
    tinydb_obs.started_event(**sample_run)

    filename = "setup.py"
    name = 'mysetup'

    tinydb_obs.artifact_event(name, filename)

    assert tinydb_obs.fs.exists(filename)

    db_run = tinydb_obs.runs.get(eid=1)
    assert db_run['artifacts'][0]['name'] == name

    with open(filename, 'rb') as f:
        file_content = f.read()

    with tinydb_obs.fs.open(db_run['artifacts'][0]['file_id']) as f2:
        fs_content = f2.read()

    assert fs_content == file_content


def test_tinydb_observer_resource_event(tinydb_obs, sample_run):
    tinydb_obs.started_event(**sample_run)

    filename = "setup.py"
    md5 = get_digest(filename)

    tinydb_obs.resource_event(filename)

    assert tinydb_obs.fs.exists(filename)

    db_run = tinydb_obs.runs.get(eid=1)
    assert db_run['resources'] == [[filename, md5]]

    with open(filename, 'rb') as f:
        file_content = f.read()

    with tinydb_obs.fs.open(db_run['resources'][0][1]) as f2:
        fs_content = f2.read()

    assert fs_content == file_content



# def test_force_bson_encodable_doesnt_change_valid_document():
#     d = {'int': 1, 'string': 'foo', 'float': 23.87, 'list': ['a', 1, True],
#          'bool': True, 'cr4zy: _but_ [legal) Key!': '$illegal.key.as.value',
#          'datetime': datetime.datetime.now(), 'tuple': (1, 2.0, 'three'),
#          'none': None}
#     assert force_bson_encodeable(d) == d


# def test_force_bson_encodable_substitutes_illegal_value_with_strings():
#     d = {
#         'a_module': datetime,
#         'some_legal_stuff': {'foo': 'bar', 'baz': [1, 23, 4]},
#         'nested': {
#             'dict': {
#                 'with': {
#                     'illegal_module': mock
#                 }
#             }
#         },
#         '$illegal': 'because it starts with a $',
#         'il.legal': 'because it contains a .',
#         12.7: 'illegal because it is not a string key'
#     }
#     expected = {
#         'a_module': str(datetime),
#         'some_legal_stuff': {'foo': 'bar', 'baz': [1, 23, 4]},
#         'nested': {
#             'dict': {
#                 'with': {
#                     'illegal_module': str(mock)
#                 }
#             }
#         },
#         '@illegal': 'because it starts with a $',
#         'il,legal': 'because it contains a .',
#         '12,7': 'illegal because it is not a string key'
#     }
#     assert force_bson_encodeable(d) == expected


# @pytest.mark.skipif(not opt.has_numpy, reason='needs numpy')
# def test_numpy_array_to_list_son_manipulator():
#     from sacred.observers.mongo import NumpyArraysToList
#     import numpy as np
#     sonm = NumpyArraysToList()
#     document = {
#         'foo': 'bar',
#         'some_array': np.eye(3),
#         'nested': {
#             'ones': np.ones(5)
#         }
#     }
#     mod_doc = sonm.transform_incoming(document, 'fake_collection')
#     assert mod_doc['foo'] == 'bar'
#     assert mod_doc['some_array'] == [[1.0, 0.0, 0.0],
#                                      [0.0, 1.0, 0.0],
#                                      [0.0, 0.0, 1.0]]
#     assert mod_doc['nested']['ones'] == [1.0, 1.0, 1.0, 1.0, 1.0]


# @pytest.mark.skipif(not opt.has_pandas, reason='needs pandas')
# def test_pandas_to_json_son_manipulator():
#     from sacred.observers.mongo import PandasToJson
#     import numpy as np
#     import pandas as pd
#     sonm = PandasToJson()
#     document = {
#         'foo': 'bar',
#         'some_array': pd.DataFrame(np.eye(3), columns=list('ABC')),
#         'nested': {
#             'ones': pd.Series(np.ones(5))
#         }
#     }
#     mod_doc = sonm.transform_incoming(document, 'fake_collection')
#     assert mod_doc['foo'] == 'bar'
#     assert mod_doc['some_array'] == {'A': {'0': 1.0, '1': 0.0, '2': 0.0},
#                                      'B': {'0': 0.0, '1': 1.0, '2': 0.0},
#                                      'C': {'0': 0.0, '1': 0.0, '2': 1.0}}
#     assert mod_doc['nested']['ones'] == {"0": 1.0, "1": 1.0, "2": 1.0,
#                                          "3": 1.0, "4": 1.0}
