#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import mock
from sacred.observers.mongo import MongoObserver
import time
import mongomock
import pytest
from copy import copy


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
    h_id = mongo_obs.hosts.insert(copy(other))

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