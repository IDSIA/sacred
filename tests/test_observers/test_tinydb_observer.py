#!/usr/bin/env python
# coding=utf-8
from __future__ import (division, print_function, unicode_literals,
                        absolute_import)

import os
import datetime
import tempfile
import io

import pytest

tinydb = pytest.importorskip("tinydb")
hashfs = pytest.importorskip("hashfs")

from tinydb import TinyDB
from hashfs import HashFS

from sacred.dependencies import get_digest
from sacred.observers.tinydb_hashfs import (TinyDbObserver, TinyDbOption, 
                                            BufferedReaderWrapper)
from sacred import optional as opt
from sacred.experiment import Experiment

T1 = datetime.datetime(1999, 5, 4, 3, 2, 1, 0)
T2 = datetime.datetime(1999, 5, 5, 5, 5, 5, 5)


@pytest.fixture()
def tinydb_obs(tmpdir):
    return TinyDbObserver.create(path=tmpdir.strpath)


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


def test_tinydb_observer_creates_missing_directories(tmpdir):
    tinydb_obs = TinyDbObserver.create(path=os.path.join(tmpdir.strpath, 'foo'))
    assert tinydb_obs.root == os.path.join(tmpdir.strpath, 'foo')


def test_tinydb_observer_started_event_creates_run(tinydb_obs, sample_run):
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


def test_tinydb_observer_started_event_saves_given_sources(tinydb_obs,
                                                           sample_run):
    filename = 'setup.py'
    md5 = get_digest(filename)

    sample_run['ex_info']['sources'] = [[filename, md5]]
    _id = tinydb_obs.started_event(**sample_run)

    assert _id is not None
    assert len(tinydb_obs.runs) == 1
    db_run = tinydb_obs.runs.get(eid=1)

    # Check all but the experiment section
    db_run_copy = db_run.copy()
    del db_run_copy['experiment']
    assert db_run_copy == {
        '_id': _id,
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

    assert len(db_run['experiment']['sources']) == 1
    assert len(db_run['experiment']['sources'][0]) == 3
    assert db_run['experiment']['sources'][0][:2] == [filename, md5]
    assert isinstance(db_run['experiment']['sources'][0][2], io.BufferedReader)

    # Check that duplicate source files are still listed in ex_info
    tinydb_obs.db_run_id = None
    tinydb_obs.started_event(**sample_run)
    assert len(tinydb_obs.runs) == 2
    db_run2 = tinydb_obs.runs.get(eid=2)

    assert (db_run['experiment']['sources'][0][:2] ==
            db_run2['experiment']['sources'][0][:2])


def test_tinydb_observer_started_event_generates_different_run_ids(tinydb_obs,
                                                                   sample_run):
    sample_run['_id'] = None
    _id = tinydb_obs.started_event(**sample_run)
    assert _id is not None

    # Check that duplicate source files are still listed in ex_info
    tinydb_obs.db_run_id = None
    sample_run['_id'] = None
    _id2 = tinydb_obs.started_event(**sample_run)

    assert len(tinydb_obs.runs) == 2
    # Check new random id is given for each run
    assert _id != _id2


def test_tinydb_observer_queued_event_is_not_implimented(tinydb_obs,
                                                         sample_run):

    sample_queued_run = sample_run.copy()
    del sample_queued_run['host_info']
    del sample_queued_run['start_time']
    sample_queued_run['queue_time'] = T1

    with pytest.raises(NotImplementedError):
        tinydb_obs.queued_event(**sample_queued_run)


def test_tinydb_observer_equality(tmpdir, tinydb_obs):

    db = TinyDB(os.path.join(tmpdir.strpath, 'metadata.json'))
    fs = HashFS(os.path.join(tmpdir.strpath, 'hashfs'), depth=3,
                width=2, algorithm='md5')
    m = TinyDbObserver(db, fs)

    assert tinydb_obs == m
    assert not tinydb_obs != m

    assert not tinydb_obs == 'foo'
    assert tinydb_obs != 'foo'


def test_tinydb_observer_heartbeat_event_updates_run(tinydb_obs, sample_run):
    tinydb_obs.started_event(**sample_run)

    info = {'my_info': [1, 2, 3], 'nr': 7}
    outp = 'some output'
    tinydb_obs.heartbeat_event(info=info, captured_out=outp, beat_time=T2)

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


def test_tinydb_observer_interrupted_event_updates_run(tinydb_obs,
                                                       sample_run):
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
    assert db_run['artifacts'][0][0] == name

    with open(filename, 'rb') as f:
        file_content = f.read()
    assert db_run['artifacts'][0][3].read() == file_content


def test_tinydb_observer_resource_event(tinydb_obs, sample_run):
    tinydb_obs.started_event(**sample_run)

    filename = "setup.py"
    md5 = get_digest(filename)

    tinydb_obs.resource_event(filename)

    assert tinydb_obs.fs.exists(filename)

    db_run = tinydb_obs.runs.get(eid=1)
    assert db_run['resources'][0][:2] == [filename, md5]

    with open(filename, 'rb') as f:
        file_content = f.read()
    assert db_run['resources'][0][2].read() == file_content


def test_tinydb_observer_resource_event_when_resource_present(tinydb_obs,
                                                              sample_run):
    tinydb_obs.started_event(**sample_run)

    filename = "setup.py"
    md5 = get_digest(filename)

    # Add file by other means
    tinydb_obs.fs.put(filename)

    tinydb_obs.resource_event(filename)

    db_run = tinydb_obs.runs.get(eid=1)
    assert db_run['resources'][0][:2] == [filename, md5]


def test_custom_bufferreaderwrapper(tmpdir):
    import copy

    with open(os.path.join(tmpdir.strpath, 'test.txt'), 'w') as f:
        f.write('some example text')
    with open(os.path.join(tmpdir.strpath, 'test.txt'), 'rb') as f:
        custom_fh = BufferedReaderWrapper(f)
        assert f.name == custom_fh.name
        assert f.mode == custom_fh.mode
        custom_fh_copy = copy.copy(custom_fh)
        assert custom_fh.name == custom_fh_copy.name
        assert custom_fh.mode == custom_fh_copy.mode

    assert f.closed
    assert not custom_fh.closed
    assert not custom_fh_copy.closed

    custom_fh_deepcopy = copy.deepcopy(custom_fh_copy)
    assert custom_fh_copy.name == custom_fh_deepcopy.name
    assert custom_fh_copy.mode == custom_fh_deepcopy.mode
    custom_fh_copy.close()
    assert custom_fh_copy.closed
    assert not custom_fh_deepcopy.closed


@pytest.mark.skipif(not opt.has_numpy, reason='needs numpy')
def test_serialisation_of_numpy_ndarray(tmpdir):
    from sacred.observers.tinydb_hashfs import NdArraySerializer
    from tinydb_serialization import SerializationMiddleware
    import numpy as np

    # Setup Serialisation object for non list/dict objects
    serialization_store = SerializationMiddleware()
    serialization_store.register_serializer(NdArraySerializer(), 'TinyArray')

    db = TinyDB(os.path.join(tmpdir.strpath, 'metadata.json'),
                storage=serialization_store)

    eye_mat = np.eye(3)
    ones_array = np.ones(5)

    document = {
        'foo': 'bar',
        'some_array': eye_mat,
        'nested': {
            'ones': ones_array
        }
    }

    db.insert(document)
    returned_doc = db.all()[0]

    assert returned_doc['foo'] == 'bar'
    assert (returned_doc['some_array'] == eye_mat).all()
    assert (returned_doc['nested']['ones'] == ones_array).all()


@pytest.mark.skipif(not opt.has_pandas, reason='needs pandas')
def test_serialisation_of_pandas_dataframe(tmpdir):
    from sacred.observers.tinydb_hashfs import (DataFrameSerializer,
                                                SeriesSerializer)
    from tinydb_serialization import SerializationMiddleware

    import numpy as np
    import pandas as pd

    # Setup Serialisation object for non list/dict objects
    serialization_store = SerializationMiddleware()
    serialization_store.register_serializer(DataFrameSerializer(),
                                            'TinyDataFrame')
    serialization_store.register_serializer(SeriesSerializer(),
                                            'TinySeries')

    db = TinyDB(os.path.join(tmpdir.strpath, 'metadata.json'),
                storage=serialization_store)

    df = pd.DataFrame(np.eye(3), columns=list('ABC'))
    series = pd.Series(np.ones(5))

    document = {
        'foo': 'bar',
        'some_dataframe': df,
        'nested': {
            'ones': series
        }
    }

    db.insert(document)
    returned_doc = db.all()[0]

    assert returned_doc['foo'] == 'bar'
    assert (returned_doc['some_dataframe'] == df).all().all()
    assert (returned_doc['nested']['ones'] == series).all()


def test_parse_tinydb_arg():
    assert TinyDbOption.parse_tinydb_arg('foo') == 'foo'


def test_parse_tinydboption_apply(tmpdir):

    exp = Experiment()
    args = os.path.join(tmpdir.strpath)

    TinyDbOption.apply(args, exp)
    assert type(exp.observers[0]) == TinyDbObserver
