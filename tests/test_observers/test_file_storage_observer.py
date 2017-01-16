#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import datetime
import hashlib
import os
import tempfile
from copy import copy
import pytest
import json

from sacred.observers.file_storage import FileStorageObserver
from sacred.serializer import restore

T1 = datetime.datetime(1999, 5, 4, 3, 2, 1, 0)
T2 = datetime.datetime(1999, 5, 5, 5, 5, 5, 5)


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


@pytest.fixture()
def dir_obs(tmpdir):
    return tmpdir, FileStorageObserver.create(tmpdir.strpath)


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


def test_fs_observer_started_event_creates_rundir(dir_obs, sample_run):
    basedir, obs = dir_obs
    sample_run['_id'] = None
    _id = obs.started_event(**sample_run)
    assert _id is not None
    run_dir = basedir.join(str(_id))
    assert run_dir.exists()
    assert run_dir.join('cout.txt').exists()
    config = json.loads(run_dir.join('config.json').read())
    assert config == sample_run['config']

    run = json.loads(run_dir.join('run.json').read())
    assert run == {
        'experiment': sample_run['ex_info'],
        'command': sample_run['command'],
        'host': sample_run['host_info'],
        'start_time': T1.isoformat(),
        'heartbeat': None,
        'meta': sample_run['meta_info'],
        "resources": [],
        "artifacts": [],
        "status": "RUNNING"
    }


def test_fs_observer_started_event_stores_source(dir_obs, sample_run, tmpfile):
    basedir, obs = dir_obs
    sample_run['ex_info']['sources'] = [[tmpfile.name, tmpfile.md5sum]]

    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)

    assert run_dir.exists()
    run = json.loads(run_dir.join('run.json').read())
    ex_info = copy(run['experiment'])
    assert ex_info['sources'][0][0] == tmpfile.name
    source_path = ex_info['sources'][0][1]
    source = basedir.join(source_path)
    assert source.exists()
    assert source.read() == 'import sacred\n'


def test_fs_observer_started_event_uses_given_id(dir_obs, sample_run):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    assert _id == sample_run['_id']
    assert basedir.join(_id).exists()


def test_fs_observer_heartbeat_event_updates_run(dir_obs, sample_run):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)
    info = {'my_info': [1, 2, 3], 'nr': 7}
    obs.heartbeat_event(info=info, captured_out='some output', beat_time=T2)

    assert run_dir.join('cout.txt').read() == 'some output'
    run = json.loads(run_dir.join('run.json').read())

    assert run['heartbeat'] == T2.isoformat()

    assert run_dir.join('info.json').exists()
    i = json.loads(run_dir.join('info.json').read())
    assert info == i


def test_fs_observer_completed_event_updates_run(dir_obs, sample_run):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)

    obs.completed_event(stop_time=T2, result=42)

    run = json.loads(run_dir.join('run.json').read())
    assert run['stop_time'] == T2.isoformat()
    assert run['status'] == 'COMPLETED'
    assert run['result'] == 42


def test_fs_observer_interrupted_event_updates_run(dir_obs, sample_run):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)

    obs.interrupted_event(interrupt_time=T2, status='CUSTOM_INTERRUPTION')

    run = json.loads(run_dir.join('run.json').read())
    assert run['stop_time'] == T2.isoformat()
    assert run['status'] == 'CUSTOM_INTERRUPTION'


def test_fs_observer_failed_event_updates_run(dir_obs, sample_run):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)

    fail_trace = "lots of errors and\nso\non..."
    obs.failed_event(fail_time=T2, fail_trace=fail_trace)

    run = json.loads(run_dir.join('run.json').read())
    assert run['stop_time'] == T2.isoformat()
    assert run['status'] == 'FAILED'
    assert run['fail_trace'] == fail_trace


def test_fs_observer_artifact_event(dir_obs, sample_run, tmpfile):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)
    
    obs.artifact_event('my_artifact.py', tmpfile.name)

    artifact = run_dir.join('my_artifact.py')
    assert artifact.exists()
    assert artifact.read() == tmpfile.content

    run = json.loads(run_dir.join('run.json').read())
    assert len(run['artifacts']) == 1
    assert run['artifacts'][0] == artifact.relto(run_dir)


def test_fs_observer_resource_event(dir_obs, sample_run, tmpfile):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)

    obs.resource_event(tmpfile.name)

    res_dir = basedir.join('_resources')
    assert res_dir.exists()
    assert len(res_dir.listdir()) == 1
    assert res_dir.listdir()[0].read() == tmpfile.content

    run = json.loads(run_dir.join('run.json').read())
    assert len(run['resources']) == 1
    assert run['resources'][0] == [tmpfile.name, res_dir.listdir()[0].strpath]


def test_fs_observer_resource_event_does_not_duplicate(dir_obs, sample_run,
                                                       tmpfile):
    basedir, obs = dir_obs
    obs2 = FileStorageObserver.create(obs.basedir)
    obs.started_event(**sample_run)

    obs.resource_event(tmpfile.name)
    # let's have another run from a different observer
    sample_run['_id'] = None
    _id = obs2.started_event(**sample_run)
    run_dir = basedir.join(str(_id))
    obs2.resource_event(tmpfile.name)

    res_dir = basedir.join('_resources')
    assert res_dir.exists()
    assert len(res_dir.listdir()) == 1
    assert res_dir.listdir()[0].read() == tmpfile.content

    run = json.loads(run_dir.join('run.json').read())
    assert len(run['resources']) == 1
    assert run['resources'][0] == [tmpfile.name, res_dir.listdir()[0].strpath]


def test_fs_observer_equality(dir_obs):
    basedir, obs = dir_obs
    obs2 = FileStorageObserver.create(obs.basedir)
    assert obs == obs2
    assert not obs != obs2

    assert not obs == 'foo'
    assert obs != 'foo'
