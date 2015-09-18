#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from copy import deepcopy
import datetime

import mock
import mongomock
import pytest
from sacred.dependencies import get_digest
from sacred.observers.mongo import (MongoObserver, MongoDbOption,
                                    force_bson_encodeable, PickleNumpyArrays)

T1 = datetime.datetime(1999, 5, 4, 3, 2, 1, 0)
T2 = datetime.datetime(1999, 5, 5, 5, 5, 5, 5)

pymongo = pytest.importorskip("pymongo")


@pytest.fixture
def mongo_obs():
    db = mongomock.MongoClient().db
    runs = db.runs
    fs = mock.MagicMock()
    return MongoObserver(runs, fs)


def test_mongo_observer_started_event_creates_run(mongo_obs):
    exp = {'name': 'test_exp', 'sources': [], 'doc': ''}
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}
    config = {'config': 'True', 'foo': 'bar', 'answer': 42}
    comment = 'test run'
    mongo_obs.started_event(exp, host, T1, config, comment)

    assert mongo_obs.runs.count() == 1
    db_run = mongo_obs.runs.find_one()
    del db_run['_id']
    assert db_run == {
        'experiment': exp,
        'host': host,
        'start_time': T1,
        'heartbeat': None,
        'info': {},
        'captured_out': '',
        'artifacts': [],
        'config': config,
        'comment': comment,
        'status': 'RUNNING',
        'resources': []
    }


def test_mongo_observer_equality(mongo_obs):
    runs = mongo_obs.runs
    fs = mock.MagicMock()
    m = MongoObserver(runs, fs)
    assert mongo_obs == m
    assert not mongo_obs != m

    assert not mongo_obs == 'foo'
    assert mongo_obs != 'foo'


def test_mongo_observer_heartbeat_event_updates_run(mongo_obs):
    exp = {'name': 'test_exp', 'sources': [], 'doc': ''}
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}

    config = {'config': 'True', 'foo': 'bar', 'answer': 42}
    mongo_obs.started_event(exp, host, T1, config, 'comment')

    info = {'my_info': [1, 2, 3], 'nr': 7}
    outp = 'some output'
    mongo_obs.heartbeat_event(info=info, captured_out=outp, beat_time=T2)

    assert mongo_obs.runs.count() == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run['heartbeat'] == T2
    assert db_run['info'] == info
    assert db_run['captured_out'] == outp


def test_mongo_observer_completed_event_updates_run(mongo_obs):
    exp = {'name': 'test_exp', 'sources': [], 'doc': ''}
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}
    config = {'config': 'True', 'foo': 'bar', 'answer': 42}
    mongo_obs.started_event(exp, host, T1, config, 'comment')

    mongo_obs.completed_event(stop_time=T2, result=42)

    assert mongo_obs.runs.count() == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run['stop_time'] == T2
    assert db_run['result'] == 42
    assert db_run['status'] == 'COMPLETED'


def test_mongo_observer_interrupted_event_updates_run(mongo_obs):
    exp = {'name': 'test_exp', 'sources': [], 'doc': ''}
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}
    config = {'config': 'True', 'foo': 'bar', 'answer': 42}
    mongo_obs.started_event(exp, host, T1, config, 'comment')

    mongo_obs.interrupted_event(interrupt_time=T2)

    assert mongo_obs.runs.count() == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run['stop_time'] == T2
    assert db_run['status'] == 'INTERRUPTED'


def test_mongo_observer_failed_event_updates_run(mongo_obs):
    exp = {'name': 'test_exp', 'sources': [], 'doc': ''}
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}
    config = {'config': 'True', 'foo': 'bar', 'answer': 42}
    mongo_obs.started_event(exp, host, T1, config, 'comment')

    fail_trace = "lots of errors and\nso\non..."
    mongo_obs.failed_event(fail_time=T2,
                           fail_trace=fail_trace)

    assert mongo_obs.runs.count() == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run['stop_time'] == T2
    assert db_run['status'] == 'FAILED'
    assert db_run['fail_trace'] == fail_trace


def test_mongo_observer_artifact_event(mongo_obs):
    exp = {'name': 'test_exp', 'sources': [], 'doc': ''}
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}
    config = {'config': 'True', 'foo': 'bar', 'answer': 42}
    mongo_obs.started_event(exp, host, T1, config, 'comment')

    filename = "setup.py"

    mongo_obs.artifact_event(filename)

    assert mongo_obs.fs.put.called
    assert mongo_obs.fs.put.call_args[1]['filename'].endswith(filename)

    db_run = mongo_obs.runs.find_one()
    assert db_run['artifacts']


def test_mongo_observer_resource_event(mongo_obs):
    exp = {'name': 'test_exp', 'sources': [], 'doc': ''}
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}
    config = {'config': 'True', 'foo': 'bar', 'answer': 42}
    mongo_obs.started_event(exp, host, T1, config, 'comment')

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


def test_pickle_numpy_arrays_son_manipulator():
    np = pytest.importorskip("numpy")
    sonm = PickleNumpyArrays()
    document = {
        'foo': 'bar',
        'some_array': np.eye(3),
        'nested': {
            'ones': np.ones(7)
        }
    }

    mod_doc = sonm.transform_incoming(deepcopy(document), 'fake_collection')
    mod_doc = force_bson_encodeable(mod_doc)
    redoc = sonm.transform_outgoing(mod_doc, 'fake_collection')
    assert redoc['foo'] == document['foo']
    assert np.all(redoc['some_array'] == document['some_array'])
    assert np.all(redoc['nested']['ones'] == document['nested']['ones'])


# ###################### MongoDbOption ###################################### #

def test_parse_mongo_db_arg():
    assert MongoDbOption.parse_mongo_db_arg('foo') == ('localhost:27017',
                                                       'foo', '')


def test_parse_mongo_db_arg_collection():
    assert MongoDbOption.parse_mongo_db_arg('foo.bar') == ('localhost:27017',
                                                           'foo', 'bar')


def test_parse_mongo_db_arg_hostname():
    assert MongoDbOption.parse_mongo_db_arg('localhost:28017') == \
        ('localhost:28017', 'sacred', '')

    assert MongoDbOption.parse_mongo_db_arg('www.mymongo.db:28017') == \
        ('www.mymongo.db:28017', 'sacred', '')

    assert MongoDbOption.parse_mongo_db_arg('123.45.67.89:27017') == \
        ('123.45.67.89:27017', 'sacred', '')


def test_parse_mongo_db_arg_hostname_dbname():
    assert MongoDbOption.parse_mongo_db_arg('localhost:28017:foo') == \
        ('localhost:28017', 'foo', '')

    assert MongoDbOption.parse_mongo_db_arg('www.mymongo.db:28017:bar') == \
        ('www.mymongo.db:28017', 'bar', '')

    assert MongoDbOption.parse_mongo_db_arg('123.45.67.89:27017:baz') == \
        ('123.45.67.89:27017', 'baz', '')


def test_parse_mongo_db_arg_hostname_dbname_collection_name():
    assert MongoDbOption.parse_mongo_db_arg('localhost:28017:foo.bar') == \
        ('localhost:28017', 'foo', 'bar')

    assert MongoDbOption.parse_mongo_db_arg('www.mymongo.db:28017:bar.baz') ==\
        ('www.mymongo.db:28017', 'bar', 'baz')

    assert MongoDbOption.parse_mongo_db_arg('123.45.67.89:27017:baz.foo') == \
        ('123.45.67.89:27017', 'baz', 'foo')
