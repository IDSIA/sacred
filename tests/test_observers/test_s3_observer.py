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
        '_id': 'FEDCBA9876543210',
        'ex_info': exp,
        'command': command,
        'host_info': host,
        'start_time': T1,
        'config': config,
        'meta_info': meta_info,
    }


@pytest.fixture
def dir_obs():
    return S3FileObserver.create(bucket=BUCKET, basedir=BASEDIR)


"""
Test that reusing the same bucket name doesn't recreate the bucket, 
        but instead reuses it (check if both _ids went to the same bucket) 
Test failing gracefully if you pass in a disallowed S3 bucket name 



Is it possible to set up a test with and without a valid credentials file? 
    I guess you can save ~/.aws/config and ~/.aws/credentials
"""

def _delete_bucket(bucket_name):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    for key in bucket.objects.all():
        key.delete()
    bucket.delete()


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
def test_fs_observer_started_event_creates_bucket(dir_obs, sample_run):
    observer = dir_obs
    sample_run['_id'] = None
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
def test_fs_observer_started_event_increments_run_id(dir_obs, sample_run):
    observer = dir_obs
    sample_run['_id'] = None
    _id = observer.started_event(**sample_run)
    _id2 = observer.started_event(**sample_run)
    assert _id + 1 == _id2
