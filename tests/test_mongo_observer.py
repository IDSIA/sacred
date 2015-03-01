#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import mock
from sacred.observers import MongoObserver
import datetime
import time
import mongomock
import pytest
from copy import copy

T1 = datetime.datetime(1999, 5, 4, 3, 2, 1, 0)
T2 = datetime.datetime(1999, 5, 5, 5, 5, 5, 5)


@pytest.fixture
def mongo_obs():
    db = mongomock.Connection().db
    experiments = db.experiments
    hosts = db.hosts
    runs = db.runs
    fs = mock.MagicMock()
    return MongoObserver(experiments, runs, hosts, fs)


def test_mongo_observer_started_event_creates_host_if_new(mongo_obs):
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}
    other = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '2.7'}
    mongo_obs.hosts.insert(copy(other))

    mongo_obs.started_event(
        {'name': 'test_exp', 'sources': [], 'doc': ''},
        copy(host),
        time.time(),
        {'config': 'True'})

    assert mongo_obs.hosts.count() == 2
    db_host = mongo_obs.hosts.find_one(host)
    db_run = mongo_obs.runs.find_one()
    assert db_run['host'].id == db_host['_id']
    assert db_run['host'].collection == 'hosts'

    del db_host['_id']
    assert db_host == host


def test_mongo_observer_started_event_uses_host_if_existing(mongo_obs):
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}
    h_id = mongo_obs.hosts.insert(copy(host))

    mongo_obs.started_event(
        {'name': 'test_exp', 'sources': [], 'doc': ''},
        copy(host),
        time.time(),
        {'config': 'True'})

    assert mongo_obs.hosts.count() == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run['host'].id == h_id
    assert db_run['host'].collection == 'hosts'


def test_mongo_observer_started_event_uses_experiment_if_existing(mongo_obs):
    exp = {'name': 'test_exp',
           'dependencies': [('pytest', '1.2.3'), ('sacred', '1.0')],
           'sources': [('/tmp/foo.py', 'abc121212ff83')],
           'doc': "mydoc"}
    e_id = mongo_obs.experiments.insert(copy(exp))

    mongo_obs.started_event(
        copy(exp),
        {'hostname': 'test'},
        time.time(),
        {'config': 'True'})

    assert mongo_obs.experiments.count() == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run['experiment'].id == e_id
    assert db_run['experiment'].collection == 'experiments'


def test_mongo_observer_started_event_creates_experiment_if_new(mongo_obs):
    exp = {'name': 'test_exp',
           'dependencies': [('pytest', '1.2.3'), ('sacred', '1.0')],
           'sources': [('/tmp/foo.py', '11111111111111')],
           'doc': "mydoc"}
    other = {'name': 'test_exp',
             'dependencies': [('pytest', '1.2.3'), ('sacred', '1.0')],
             'sources': [('/tmp/foo.py', '22222222222222')],
             'doc': "mydoc"}
    e_id = mongo_obs.experiments.insert(copy(other))

    mongo_obs.started_event(
        copy(exp),
        {'hostname': 'test'},
        time.time(),
        {'config': 'True'})

    assert mongo_obs.experiments.count() == 2
    db_exp = mongo_obs.experiments.find_one(exp)
    db_run = mongo_obs.runs.find_one()
    assert db_run['experiment'].id == db_exp['_id']
    assert db_run['experiment'].collection == 'experiments'

    del db_exp['_id']
    assert db_exp == exp


def test_mongo_observer_started_event_creates_run(mongo_obs):
    exp = {'name': 'test_exp', 'sources': [], 'doc': ''}
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}
    config = {'config': 'True', 'foo': 'bar', 'answer': 42}
    mongo_obs.started_event(exp, host, T1, config)

    assert mongo_obs.runs.count() == 1
    db_run = mongo_obs.runs.find_one()
    del db_run['_id']
    del db_run['host']
    del db_run['experiment']
    assert db_run == {
        'start_time': T1,
        'heartbeat': None,
        'info': {},
        'captured_out': '',
        'artifacts': [],
        'config': config,
        'status': 'RUNNING',
        'resources': []
    }


def test_mongo_observer_heartbeat_event_updates_run(mongo_obs):
    exp = {'name': 'test_exp', 'sources': [], 'doc': ''}
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}

    config = {'config': 'True', 'foo': 'bar', 'answer': 42}
    mongo_obs.started_event(exp, host, T1, config)

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
    mongo_obs.started_event(exp, host, T1, config)

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
    mongo_obs.started_event(exp, host, T1, config)

    mongo_obs.interrupted_event(interrupt_time=T2)

    assert mongo_obs.runs.count() == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run['stop_time'] == T2
    assert db_run['status'] == 'INTERRUPTED'


def test_mongo_observer_failed_event_updates_run(mongo_obs):
    exp = {'name': 'test_exp', 'sources': [], 'doc': ''}
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}
    config = {'config': 'True', 'foo': 'bar', 'answer': 42}
    mongo_obs.started_event(exp, host, T1, config)

    fail_trace = "lots of errors and\nso\non..."
    mongo_obs.failed_event(fail_time=T2,
                           fail_trace=fail_trace)

    assert mongo_obs.runs.count() == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run['stop_time'] == T2
    assert db_run['status'] == 'FAILED'
    assert db_run['fail_trace'] == fail_trace
