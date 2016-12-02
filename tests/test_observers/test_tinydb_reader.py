#!/usr/bin/env python
# coding=utf-8
from __future__ import (division, print_function, unicode_literals,
                        absolute_import)

import datetime
import tempfile
import io

import pytest

tinydb = pytest.importorskip("tinydb")
hashfs = pytest.importorskip("hashfs")

from tinydb import Query

from sacred.dependencies import get_digest
from sacred.observers.tinydb_hashfs import TinyDbObserver, TinyDbReader


# Utilities and fixtures
@pytest.fixture
def sample_run():

    T1 = datetime.datetime(1999, 5, 4, 3, 2, 1, 0)

    exp = {
        'name': 'test_exp',
        'sources': [],
        'doc': '',
        'base_dir': '/tmp',
        'dependencies': ['sacred==0.7b0']
    }
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}
    config = {'config': 'True', 'foo': 'bar', 'answer': 42}
    command = 'run'
    meta_info = {'comment': 'test run'}
    sample_run = {
        '_id': 'FED235DA13',
        'ex_info': exp,
        'command': command,
        'host_info': host,
        'start_time': T1,
        'config': config,
        'meta_info': meta_info,
    }

    filename = 'setup.py'
    md5 = get_digest(filename)
    sample_run['ex_info']['sources'] = [[filename, md5]]

    return sample_run


def run_test_experiment(exp_name, exp_id, root_dir):

    T2 = datetime.datetime(1999, 5, 5, 5, 5, 5, 5)
    T3 = datetime.datetime(1999, 5, 5, 6, 6, 6, 6)

    run_date = sample_run()
    run_date['ex_info']['name'] = exp_name
    run_date['_id'] = exp_id

    # Create
    tinydb_obs = TinyDbObserver.create(path=root_dir)

    # Start exp 1
    tinydb_obs.started_event(**run_date)

    # Heartbeat
    info = {'my_info': [1, 2, 3], 'nr': 7}
    outp = 'some output'
    tinydb_obs.heartbeat_event(info=info, captured_out=outp, beat_time=T2)
    # Add Artifact
    filename = "sacred/__about__.py"
    name = 'about'
    tinydb_obs.artifact_event(name, filename)

    # Add Resource
    filename = "sacred/__init__.py"
    tinydb_obs.resource_event(filename)

    # Complete
    tinydb_obs.completed_event(stop_time=T3, result=42)

    return tinydb_obs


def strip_file_handles(results):
    """Return a database result set with all file handle objects removed.abs

    Utility function to aid comparison of database entries. As file handles are
    created newly each object, these are always different so can be excluded.
    """

    if not isinstance(results, (list, tuple)):
        results = [results]

    cleaned_results = []
    for result in results:
        sources = result['experiment']['sources']
        artifacts = result['artifacts']
        resources = result['resources']
        if sources:
            for src in sources:
                if isinstance(src[-1], io.BufferedReader):
                    del src[-1]
        if artifacts:
            for art in artifacts:
                if isinstance(art[-1], io.BufferedReader):
                    del art[-1]
        if resources:
            for res in resources:
                if isinstance(res[-1], io.BufferedReader):
                    del res[-1]
        cleaned_results.append(result)

    return cleaned_results


# TinyDbReader Tests
def test_tinydb_reader_loads_db_and_fs(tmpdir):

    root = tmpdir.strpath
    tinydb_obs = run_test_experiment(exp_name='exp1', exp_id='1234', root_dir=root)
    tinydb_reader = TinyDbReader(root)

    assert tinydb_obs.fs.root == tinydb_reader.fs.root
    # Different file handles are used in each object so compar based on str
    # representation
    assert str(tinydb_obs.runs.all()[0]) == str(tinydb_reader.runs.all()[0])


def test_tinydb_reader_raises_exceptions(tmpdir):
    with pytest.raises(IOError):
        TinyDbReader('foo')


def test_fetch_metadata_function_with_indices(tmpdir, sample_run):

    # Setup and run three experiments
    root = tmpdir.strpath
    tinydb_obs = run_test_experiment(exp_name='experiment 1 alpha',
                                     exp_id='1234', root_dir=root)
    tinydb_obs = run_test_experiment(exp_name='experiment 2 beta',
                                     exp_id='5678', root_dir=root)
    tinydb_obs = run_test_experiment(exp_name='experiment 3 alpha',
                                     exp_id='9990', root_dir=root)

    tinydb_reader = TinyDbReader(root)

    # Test fetch by indices
    res = tinydb_reader.fetch_metadata(indices=-1)
    res2 = tinydb_reader.fetch_metadata(indices=[-1])
    assert strip_file_handles(res) == strip_file_handles(res2)
    res3 = tinydb_reader.fetch_metadata(indices=[0, -1])
    assert len(res3) == 2

    exp1_res = tinydb_reader.fetch_metadata(indices=0)
    assert len(exp1_res) == 1
    assert exp1_res[0]['experiment']['name'] == 'experiment 1 alpha'
    assert exp1_res[0]['_id'] == '1234'

    # Test Exception
    with pytest.raises(ValueError):
        tinydb_reader.fetch_metadata(indices=4)

    # Test returned values
    exp1 = strip_file_handles(exp1_res)[0]

    sample_run['ex_info']['name'] = 'experiment 1 alpha'
    sample_run['ex_info']['sources'] = [
        ['setup.py', get_digest('setup.py')]
    ]

    assert exp1 == {
        '_id': '1234',
        'experiment': sample_run['ex_info'],
        'format': tinydb_obs.VERSION,
        'command': sample_run['command'],
        'host': sample_run['host_info'],
        'start_time': sample_run['start_time'],
        'heartbeat': datetime.datetime(1999, 5, 5, 5, 5, 5, 5),
        'info': {'my_info': [1, 2, 3], 'nr': 7},
        'captured_out': 'some output',
        'artifacts': [
            ['about', 'sacred/__about__.py', get_digest('sacred/__about__.py')]
        ],
        'config': sample_run['config'],
        'meta': sample_run['meta_info'],
        'status': 'COMPLETED',
        'resources': [
            ['sacred/__init__.py', get_digest('sacred/__init__.py')]
        ],
        'result': 42,
        'stop_time': datetime.datetime(1999, 5, 5, 6, 6, 6, 6)
    }


def test_fetch_metadata_function_with_exp_name(tmpdir):

    # Setup and run three experiments
    root = tmpdir.strpath
    run_test_experiment(exp_name='experiment 1 alpha',
                        exp_id='1234', root_dir=root)
    run_test_experiment(exp_name='experiment 2 beta',
                        exp_id='5678', root_dir=root)
    run_test_experiment(exp_name='experiment 3 alpha',
                        exp_id='9990', root_dir=root)

    tinydb_reader = TinyDbReader(root)

    # Test Fetch by exp name
    res1 = tinydb_reader.fetch_metadata(exp_name='alpha')
    assert len(res1) == 2
    res2 = tinydb_reader.fetch_metadata(exp_name='experiment 1')
    assert len(res2) == 1
    assert res2[0]['experiment']['name'] == 'experiment 1 alpha'
    res2 = tinydb_reader.fetch_metadata(exp_name='foo')
    assert len(res2) == 0


def test_fetch_metadata_function_with_querry(tmpdir):

    # Setup and run three experiments
    root = tmpdir.strpath
    run_test_experiment(exp_name='experiment 1 alpha',
                        exp_id='1234', root_dir=root)
    run_test_experiment(exp_name='experiment 2 beta',
                        exp_id='5678', root_dir=root)
    run_test_experiment(exp_name='experiment 3 alpha beta',
                        exp_id='9990', root_dir=root)

    tinydb_reader = TinyDbReader(root)

    record = Query()

    exp1_query = record.experiment.name.matches('.*alpha$')

    exp3_query = (
        (record.experiment.name.search('alpha')) &
        (record._id == '9990')
    )

    # Test Fetch by Tinydb Query
    res1 = tinydb_reader.fetch_metadata(query=exp1_query)
    assert len(res1) == 1
    assert res1[0]['experiment']['name'] == 'experiment 1 alpha'

    res2 = tinydb_reader.fetch_metadata(
        query=record.experiment.name.search('experiment [23]'))
    assert len(res2) == 2

    res3 = tinydb_reader.fetch_metadata(query=exp3_query)
    assert len(res3) == 1
    assert res3[0]['experiment']['name'] == 'experiment 3 alpha beta'

    # Test Exception
    with pytest.raises(ValueError):
        tinydb_reader.fetch_metadata()


def test_search_function(tmpdir):

    # Setup and run three experiments
    root = tmpdir.strpath
    run_test_experiment(exp_name='experiment 1 alpha',
                        exp_id='1234', root_dir=root)
    run_test_experiment(exp_name='experiment 2 beta',
                        exp_id='5678', root_dir=root)
    run_test_experiment(exp_name='experiment 3 alpha beta',
                        exp_id='9990', root_dir=root)

    tinydb_reader = TinyDbReader(root)

    # Test Fetch by Tinydb Query in search function
    record = Query()
    q = record.experiment.name.search('experiment [23]')

    res = tinydb_reader.search(q)
    assert len(res) == 2
    res2 = tinydb_reader.fetch_metadata(query=q)
    assert strip_file_handles(res) == strip_file_handles(res2)


def test_fetch_files_function(tmpdir):
    # Setup and run three experiments
    root = tmpdir.strpath
    run_test_experiment(exp_name='experiment 1 alpha',
                        exp_id='1234', root_dir=root)
    run_test_experiment(exp_name='experiment 2 beta',
                        exp_id='5678', root_dir=root)
    run_test_experiment(exp_name='experiment 3 alpha beta',
                        exp_id='9990', root_dir=root)

    tinydb_reader = TinyDbReader(root)

    res = tinydb_reader.fetch_files(indices=0)
    assert len(res) == 1
    assert list(res[0]['artifacts'].keys()) == ['about']
    assert isinstance(res[0]['artifacts']['about'], io.BufferedReader)
    assert res[0]['date'] == datetime.datetime(1999, 5, 4, 3, 2, 1)
    assert res[0]['exp_id'] == '1234'
    assert res[0]['exp_name'] == 'experiment 1 alpha'
    assert list(res[0]['resources'].keys()) == ['sacred/__init__.py']
    assert isinstance(res[0]['resources']['sacred/__init__.py'], io.BufferedReader)
    assert list(res[0]['sources'].keys()) == ['setup.py']
    assert isinstance(res[0]['sources']['setup.py'], io.BufferedReader)


def test_fetch_report_function(tmpdir):

    # Setup and run three experiments
    root = tmpdir.strpath
    run_test_experiment(exp_name='experiment 1 alpha',
                        exp_id='1234', root_dir=root)
    run_test_experiment(exp_name='experiment 2 beta',
                        exp_id='5678', root_dir=root)
    run_test_experiment(exp_name='experiment 3 alpha beta',
                        exp_id='9990', root_dir=root)

    tinydb_reader = TinyDbReader(root)

    res = tinydb_reader.fetch_report(indices=0)

    target = """
-------------------------------------------------
Experiment: experiment 1 alpha
-------------------------------------------------
ID: 1234
Date: Tue 04 May 1999    Duration: 27:04:05.0

Parameters:
    answer: 42
    config: True
    foo: bar

Result:
    42

Dependencies:
    sacred==0.7b0

Resources:
    sacred/__init__.py

Source Files:
    setup.py

Outputs:
    about
"""

    assert res[0] == target
