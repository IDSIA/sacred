#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import datetime
import hashlib
import os

import pytest
import tempfile
from sacred.serializer import json

sqlalchemy = pytest.importorskip("sqlalchemy")

from sacred.observers.sql import (SqlObserver, Host, Experiment, Run, Source,
                                  Resource)

T1 = datetime.datetime(1999, 5, 4, 3, 2, 1, 0)
T2 = datetime.datetime(1999, 5, 5, 5, 5, 5, 5)


@pytest.fixture
def engine(request):
    """Engine configuration."""
    url = request.config.getoption("--sqlalchemy-connect-url")
    from sqlalchemy.engine import create_engine
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    from sqlalchemy.orm import sessionmaker
    connection = engine.connect()
    trans = connection.begin()
    session = sessionmaker()(bind=connection)
    yield session
    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture
def sql_obs(session, engine):
    return SqlObserver(engine, session)


@pytest.fixture
def sample_run():
    exp = {'name': 'test_exp', 'sources': [], 'dependencies': [],
           'base_dir': '/tmp'}
    host = {'hostname': 'test_host', 'cpu': 'Intel', 'os': ['Linux', 'Ubuntu'],
            'python_version': '3.4'}
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


@pytest.fixture
def tmpfile():
    # NOTE: instead of using a with block and delete=True we are creating and
    # manually deleting the file, such that we can close it before running the
    # tests. This is necessary since on Windows we can not open the same file
    # twice, so for the FileStorageObserver to read it, we need to close it.
    f = tempfile.NamedTemporaryFile(suffix='.py', delete=False)

    f.content = 'import sacred\n'
    f.write(f.content.encode())
    f.flush()
    f.seek(0)
    f.md5sum = hashlib.md5(f.read()).hexdigest()

    f.close()

    yield f

    os.remove(f.name)


def test_sql_observer_started_event_creates_run(sql_obs, sample_run, session):
    sample_run['_id'] = None
    _id = sql_obs.started_event(**sample_run)
    assert _id is not None
    assert session.query(Run).count() == 1
    assert session.query(Host).count() == 1
    assert session.query(Experiment).count() == 1
    run = session.query(Run).first()
    assert run.to_json() == {
            '_id': _id,
            'command': sample_run['command'],
            'start_time': sample_run['start_time'],
            'heartbeat': None,
            'stop_time': None,
            'queue_time': None,
            'status': 'RUNNING',
            'result': None,
            'meta': {
                'comment': sample_run['meta_info']['comment'],
                'priority': 0.0},
            'resources': [],
            'artifacts': [],
            'host': sample_run['host_info'],
            'experiment': sample_run['ex_info'],
            'config': sample_run['config'],
            'captured_out': None,
            'fail_trace': None,
        }


def test_sql_observer_started_event_uses_given_id(sql_obs, sample_run, session):
    _id = sql_obs.started_event(**sample_run)
    assert _id == sample_run['_id']
    assert session.query(Run).count() == 1
    db_run = session.query(Run).first()
    assert db_run.run_id == sample_run['_id']


def test_fs_observer_started_event_saves_source(sql_obs, sample_run, session,
                                                tmpfile):
    sample_run['ex_info']['sources'] = [[tmpfile.name, tmpfile.md5sum]]

    sql_obs.started_event(**sample_run)

    assert session.query(Run).count() == 1
    db_run = session.query(Run).first()
    assert session.query(Source).count() == 1
    assert len(db_run.experiment.sources) == 1
    source = db_run.experiment.sources[0]
    assert source.filename == tmpfile.name
    assert source.content == 'import sacred\n'
    assert source.md5sum == tmpfile.md5sum


def test_sql_observer_heartbeat_event_updates_run(sql_obs, sample_run, session):
    sql_obs.started_event(**sample_run)

    info = {'my_info': [1, 2, 3], 'nr': 7}
    outp = 'some output'
    sql_obs.heartbeat_event(info=info, captured_out=outp, beat_time=T2)

    assert session.query(Run).count() == 1
    db_run = session.query(Run).first()
    assert db_run.heartbeat == T2
    assert json.decode(db_run.info) == info
    assert db_run.captured_out == outp


def test_sql_observer_completed_event_updates_run(sql_obs, sample_run, session):
    sql_obs.started_event(**sample_run)
    sql_obs.completed_event(stop_time=T2, result=42)

    assert session.query(Run).count() == 1
    db_run = session.query(Run).first()

    assert db_run.stop_time == T2
    assert db_run.result == 42
    assert db_run.status == 'COMPLETED'


def test_sql_observer_interrupted_event_updates_run(sql_obs, sample_run, session):
    sql_obs.started_event(**sample_run)
    sql_obs.interrupted_event(interrupt_time=T2, status='INTERRUPTED')

    assert session.query(Run).count() == 1
    db_run = session.query(Run).first()

    assert db_run.stop_time == T2
    assert db_run.status == 'INTERRUPTED'


def test_sql_observer_failed_event_updates_run(sql_obs, sample_run, session):
    sql_obs.started_event(**sample_run)
    fail_trace = ["lots of errors and", "so", "on..."]
    sql_obs.failed_event(fail_time=T2, fail_trace=fail_trace)

    assert session.query(Run).count() == 1
    db_run = session.query(Run).first()

    assert db_run.stop_time == T2
    assert db_run.status == 'FAILED'
    assert db_run.fail_trace == "lots of errors and\nso\non..."


def test_sql_observer_artifact_event(sql_obs, sample_run, session, tmpfile):
    sql_obs.started_event(**sample_run)

    sql_obs.artifact_event('my_artifact.py', tmpfile.name)

    assert session.query(Run).count() == 1
    db_run = session.query(Run).first()

    assert len(db_run.artifacts) == 1
    artifact = db_run.artifacts[0]

    assert artifact.filename == 'my_artifact.py'
    assert artifact.content.decode() == tmpfile.content


def test_fs_observer_resource_event(sql_obs, sample_run, session, tmpfile):
    sql_obs.started_event(**sample_run)

    sql_obs.resource_event(tmpfile.name)

    assert session.query(Run).count() == 1
    db_run = session.query(Run).first()

    assert len(db_run.resources) == 1
    res = db_run.resources[0]
    assert res.filename == tmpfile.name
    assert res.md5sum == tmpfile.md5sum
    assert res.content.decode() == tmpfile.content


def test_fs_observer_doesnt_duplicate_sources(sql_obs, sample_run, session, tmpfile):
    sql_obs2 = SqlObserver(sql_obs.engine, session)
    sample_run['_id'] = None
    sample_run['ex_info']['sources'] = [[tmpfile.name, tmpfile.md5sum]]

    sql_obs.started_event(**sample_run)
    sql_obs2.started_event(**sample_run)

    assert session.query(Run).count() == 2
    assert session.query(Source).count() == 1


def test_fs_observer_doesnt_duplicate_resources(sql_obs, sample_run, session, tmpfile):
    sql_obs2 = SqlObserver(sql_obs.engine, session)
    sample_run['_id'] = None
    sample_run['ex_info']['sources'] = [[tmpfile.name, tmpfile.md5sum]]

    sql_obs.started_event(**sample_run)
    sql_obs2.started_event(**sample_run)

    sql_obs.resource_event(tmpfile.name)
    sql_obs2.resource_event(tmpfile.name)

    assert session.query(Run).count() == 2
    assert session.query(Resource).count() == 1


def test_sql_observer_equality(sql_obs, engine, session):
    sql_obs2 = SqlObserver(engine, session)
    assert sql_obs == sql_obs2

    assert not sql_obs != sql_obs2

    assert not sql_obs == 'foo'
    assert sql_obs != 'foo'
