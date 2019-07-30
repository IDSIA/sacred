#!/usr/bin/env python
# coding=utf-8

from moto import mock_s3

import datetime
import os
import pytest
import json

from sacred.observers import S3FileObserver

import boto3
from botocore.exceptions import ClientError

T1 = datetime.datetime(1999, 5, 4, 3, 2, 1, 0)
T2 = datetime.datetime(1999, 5, 5, 5, 5, 5, 5)

BUCKET = 'pytest-s3-observer-bucket'
BASEDIR = 'some-tests'

@pytest.fixture()
def sample_run():
    exp = {'name': 'test_exp', 'sources': [], 'doc': '', 'base_dir': '/tmp'}
    host = {'hostname': 'test_host', 'cpu_count': 1, 'python_version': '3.4'}
    config = {'config': 'True', 'foo': 'bar', 'answer': 42}
    command = 'run'
    meta_info = {'comment': 'test run'}
    return {
        '_id': None,
        'ex_info': exp,
        'command': command,
        'host_info': host,
        'start_time': T1,
        'config': config,
        'meta_info': meta_info,
    }


@pytest.fixture
def observer():
    return S3FileObserver.create(bucket=BUCKET, basedir=BASEDIR)


def _bucket_exists(bucket_name):
    s3 = boto3.resource('s3')
    try:
        s3.meta.client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
    return True


def _key_exists(bucket_name, key):
    s3 = boto3.resource('s3')
    try:
        s3.Object(bucket_name, key).load()
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
    return True


def _get_file_data(bucket_name, key):
    s3 = boto3.resource('s3')
    return s3.Object(bucket_name, key).get()['Body'].read()


@mock_s3
def test_fs_observer_started_event_creates_bucket(observer, sample_run):
    _id = observer.started_event(**sample_run)
    run_dir = os.path.join(BASEDIR, str(_id))
    assert _bucket_exists(bucket_name=BUCKET)
    assert _key_exists(bucket_name=BUCKET,
                       key=os.path.join(run_dir, 'cout.txt'))
    assert _key_exists(bucket_name=BUCKET,
                       key=os.path.join(run_dir, 'config.json'))
    assert _key_exists(bucket_name=BUCKET,
                       key=os.path.join(run_dir, 'run.json'))
    config = _get_file_data(bucket_name=BUCKET,
                            key=os.path.join(run_dir, 'config.json'))

    assert json.loads(config.decode('utf-8')) == sample_run['config']
    run = _get_file_data(bucket_name=BUCKET,
                         key=os.path.join(run_dir, 'run.json'))
    assert json.loads(run.decode('utf-8')) == {
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


@mock_s3
def test_fs_observer_started_event_increments_run_id(observer, sample_run):
    _id = observer.started_event(**sample_run)
    _id2 = observer.started_event(**sample_run)
    assert _id + 1 == _id2


def test_s3_observer_equality():
    obs_one = S3FileObserver.create(bucket=BUCKET, basedir=BASEDIR)
    obs_two = S3FileObserver.create(bucket=BUCKET, basedir=BASEDIR)
    different_basedir = S3FileObserver.create(bucket=BUCKET,
                                              basedir="another/dir")
    assert obs_one == obs_two
    assert obs_one != different_basedir


@mock_s3
def test_raises_error_on_duplicate_id_directory(observer, sample_run):
    observer.started_event(**sample_run)
    sample_run['_id'] = 1
    with pytest.raises(FileExistsError):
        observer.started_event(**sample_run)


def test_raises_error_on_invalid_bucket_name():
    with pytest.raises(ValueError):
        _ = S3FileObserver.create(bucket="this_bucket_is_invalid",
                                  basedir=BASEDIR)
