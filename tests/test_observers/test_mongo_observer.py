#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import datetime

import mock
import mongomock
import pytest
from sacred.dependencies import get_digest
from sacred.observers.mongo import (MongoObserver, force_bson_encodeable)
from sacred import optional as opt

T1 = datetime.datetime(1999, 5, 4, 3, 2, 1, 0)
T2 = datetime.datetime(1999, 5, 5, 5, 5, 5, 5)

pymongo = pytest.importorskip("pymongo")


@pytest.fixture
def mongo_obs():
    db = mongomock.MongoClient().db
    runs = db.runs
    fs = mock.MagicMock()
    return MongoObserver(runs, fs)


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


def test_mongo_observer_started_event_creates_run(mongo_obs, sample_run):
    sample_run['_id'] = None
    _id = mongo_obs.started_event(**sample_run)
    assert _id is not None
    assert mongo_obs.runs.count() == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run == {
        '_id': _id,
        'experiment': sample_run['ex_info'],
        'format': mongo_obs.VERSION,
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


def test_mongo_observer_started_event_uses_given_id(mongo_obs, sample_run):
    _id = mongo_obs.started_event(**sample_run)
    assert _id == sample_run['_id']
    assert mongo_obs.runs.count() == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run['_id'] == sample_run['_id']


def test_mongo_observer_equality(mongo_obs):
    runs = mongo_obs.runs
    fs = mock.MagicMock()
    m = MongoObserver(runs, fs)
    assert mongo_obs == m
    assert not mongo_obs != m

    assert not mongo_obs == 'foo'
    assert mongo_obs != 'foo'


def test_mongo_observer_heartbeat_event_updates_run(mongo_obs, sample_run):
    mongo_obs.started_event(**sample_run)

    info = {'my_info': [1, 2, 3], 'nr': 7}
    outp = 'some output'
    mongo_obs.heartbeat_event(info=info, captured_out=outp, beat_time=T2)

    assert mongo_obs.runs.count() == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run['heartbeat'] == T2
    assert db_run['info'] == info
    assert db_run['captured_out'] == outp


def test_mongo_observer_completed_event_updates_run(mongo_obs, sample_run):
    mongo_obs.started_event(**sample_run)

    mongo_obs.completed_event(stop_time=T2, result=42)

    assert mongo_obs.runs.count() == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run['stop_time'] == T2
    assert db_run['result'] == 42
    assert db_run['status'] == 'COMPLETED'


def test_mongo_observer_interrupted_event_updates_run(mongo_obs, sample_run):
    mongo_obs.started_event(**sample_run)

    mongo_obs.interrupted_event(interrupt_time=T2, status='INTERRUPTED')

    assert mongo_obs.runs.count() == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run['stop_time'] == T2
    assert db_run['status'] == 'INTERRUPTED'


def test_mongo_observer_failed_event_updates_run(mongo_obs, sample_run):
    mongo_obs.started_event(**sample_run)

    fail_trace = "lots of errors and\nso\non..."
    mongo_obs.failed_event(fail_time=T2,
                           fail_trace=fail_trace)

    assert mongo_obs.runs.count() == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run['stop_time'] == T2
    assert db_run['status'] == 'FAILED'
    assert db_run['fail_trace'] == fail_trace


def test_mongo_observer_artifact_event(mongo_obs, sample_run):
    mongo_obs.started_event(**sample_run)

    filename = "setup.py"
    name = 'mysetup'

    mongo_obs.artifact_event(name, filename)

    assert mongo_obs.fs.put.called
    assert mongo_obs.fs.put.call_args[1]['filename'].endswith(name)

    db_run = mongo_obs.runs.find_one()
    assert db_run['artifacts']


def test_mongo_observer_resource_event(mongo_obs, sample_run):
    mongo_obs.started_event(**sample_run)

    filename = "setup.py"
    md5 = get_digest(filename)

    mongo_obs.resource_event(filename)

    assert mongo_obs.fs.exists.called
    mongo_obs.fs.exists.assert_any_call(filename=filename)

    db_run = mongo_obs.runs.find_one()
    assert db_run['resources'] == [(filename, md5)]


def test_force_bson_encodable_doesnt_change_valid_document():
    d = {'int': 1, 'string': 'foo', 'float': 23.87, 'list': ['a', 1, True],
         'bool': True, 'cr4zy: _but_ [legal) Key!': '$illegal.key.as.value',
         'datetime': datetime.datetime.now(), 'tuple': (1, 2.0, 'three'),
         'none': None}
    assert force_bson_encodeable(d) == d


def test_force_bson_encodable_substitutes_illegal_value_with_strings():
    d = {
        'a_module': datetime,
        'some_legal_stuff': {'foo': 'bar', 'baz': [1, 23, 4]},
        'nested': {
            'dict': {
                'with': {
                    'illegal_module': mock
                }
            }
        },
        '$illegal': 'because it starts with a $',
        'il.legal': 'because it contains a .',
        12.7: 'illegal because it is not a string key'
    }
    expected = {
        'a_module': str(datetime),
        'some_legal_stuff': {'foo': 'bar', 'baz': [1, 23, 4]},
        'nested': {
            'dict': {
                'with': {
                    'illegal_module': str(mock)
                }
            }
        },
        '@illegal': 'because it starts with a $',
        'il,legal': 'because it contains a .',
        '12,7': 'illegal because it is not a string key'
    }
    assert force_bson_encodeable(d) == expected


@pytest.mark.skipif(not opt.has_numpy, reason='needs numpy')
def test_numpy_array_to_list_son_manipulator():
    from sacred.observers.mongo import NumpyArraysToList
    import numpy as np
    sonm = NumpyArraysToList()
    document = {
        'foo': 'bar',
        'some_array': np.eye(3),
        'nested': {
            'ones': np.ones(5)
        }
    }
    mod_doc = sonm.transform_incoming(document, 'fake_collection')
    assert mod_doc['foo'] == 'bar'
    assert mod_doc['some_array'] == [[1.0, 0.0, 0.0],
                                     [0.0, 1.0, 0.0],
                                     [0.0, 0.0, 1.0]]
    assert mod_doc['nested']['ones'] == [1.0, 1.0, 1.0, 1.0, 1.0]


@pytest.mark.skipif(not opt.has_pandas, reason='needs pandas')
def test_pandas_to_json_son_manipulator():
    from sacred.observers.mongo import PandasToJson
    import numpy as np
    import pandas as pd
    sonm = PandasToJson()
    document = {
        'foo': 'bar',
        'some_array': pd.DataFrame(np.eye(3), columns=list('ABC')),
        'nested': {
            'ones': pd.Series(np.ones(5))
        }
    }
    mod_doc = sonm.transform_incoming(document, 'fake_collection')
    assert mod_doc['foo'] == 'bar'
    assert mod_doc['some_array'] == {'A': {'0': 1.0, '1': 0.0, '2': 0.0},
                                     'B': {'0': 0.0, '1': 1.0, '2': 0.0},
                                     'C': {'0': 0.0, '1': 0.0, '2': 1.0}}
    assert mod_doc['nested']['ones'] == {"0": 1.0, "1": 1.0, "2": 1.0,
                                         "3": 1.0, "4": 1.0}
