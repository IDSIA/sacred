#!/usr/bin/env python
# coding=utf-8

import datetime
import pytest
import json

from sacred.observers import S3Observer

moto = pytest.importorskip("moto")
boto3 = pytest.importorskip("boto3")
pytest.importorskip("botocore")

T1 = datetime.datetime(1999, 5, 4, 3, 2, 1, 0)
T2 = datetime.datetime(1999, 5, 5, 5, 5, 5, 5)

BUCKET = "pytest-s3-observer-bucket"
BASEDIR = "some-tests"
REGION = "us-west-2"


def s3_join(*args):
    return "/".join(args)


@pytest.fixture()
def sample_run():
    exp = {"name": "test_exp", "sources": [], "doc": "", "base_dir": "/tmp"}
    host = {"hostname": "test_host", "cpu_count": 1, "python_version": "3.4"}
    config = {"config": "True", "foo": "bar", "answer": 42}
    command = "run"
    meta_info = {"comment": "test run"}
    return {
        "_id": None,
        "ex_info": exp,
        "command": command,
        "host_info": host,
        "start_time": T1,
        "config": config,
        "meta_info": meta_info,
    }


@pytest.fixture
def observer():
    return S3Observer(bucket=BUCKET, basedir=BASEDIR, region=REGION)


def _bucket_exists(bucket_name):
    from botocore.exceptions import ClientError

    s3 = boto3.resource("s3")
    try:
        s3.meta.client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
    return True


def _key_exists(bucket_name, key):
    s3 = boto3.resource("s3")
    try:
        s3.Object(bucket_name, key).load()
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
    return True


def _get_file_data(bucket_name, key):
    s3 = boto3.resource("s3")
    return s3.Object(bucket_name, key).get()["Body"].read()


@moto.mock_s3
def test_fs_observer_started_event_creates_bucket(observer, sample_run):
    _id = observer.started_event(**sample_run)
    run_dir = s3_join(BASEDIR, str(_id))
    assert _bucket_exists(bucket_name=BUCKET)
    assert _key_exists(bucket_name=BUCKET, key=s3_join(run_dir, "cout.txt"))
    assert _key_exists(bucket_name=BUCKET, key=s3_join(run_dir, "config.json"))
    assert _key_exists(bucket_name=BUCKET, key=s3_join(run_dir, "run.json"))
    config = _get_file_data(bucket_name=BUCKET, key=s3_join(run_dir, "config.json"))

    assert json.loads(config.decode("utf-8")) == sample_run["config"]
    run = _get_file_data(bucket_name=BUCKET, key=s3_join(run_dir, "run.json"))
    assert json.loads(run.decode("utf-8")) == {
        "experiment": sample_run["ex_info"],
        "command": sample_run["command"],
        "host": sample_run["host_info"],
        "start_time": T1.isoformat(),
        "heartbeat": None,
        "meta": sample_run["meta_info"],
        "resources": [],
        "artifacts": [],
        "status": "RUNNING",
    }


@moto.mock_s3
def test_fs_observer_started_event_increments_run_id(observer, sample_run):
    _id = observer.started_event(**sample_run)
    _id2 = observer.started_event(**sample_run)
    assert _id + 1 == _id2


def test_s3_observer_equality():
    obs_one = S3Observer(bucket=BUCKET, basedir=BASEDIR, region=REGION)
    obs_two = S3Observer(bucket=BUCKET, basedir=BASEDIR, region=REGION)
    different_basedir = S3Observer(bucket=BUCKET, basedir="another/dir", region=REGION)
    different_bucket = S3Observer(bucket="other-bucket", basedir=BASEDIR, region=REGION)
    assert obs_one == obs_two
    assert obs_one != different_basedir
    assert obs_one != different_bucket


@moto.mock_s3
def test_raises_error_on_duplicate_id_directory(observer, sample_run):
    observer.started_event(**sample_run)
    sample_run["_id"] = 1
    with pytest.raises(FileExistsError):
        observer.started_event(**sample_run)


@moto.mock_s3
def test_completed_event_updates_run_json(observer, sample_run):
    observer.started_event(**sample_run)
    run = json.loads(
        _get_file_data(
            bucket_name=BUCKET, key=s3_join(observer.dir, "run.json")
        ).decode("utf-8")
    )
    assert run["status"] == "RUNNING"
    observer.completed_event(T2, "success!")
    run = json.loads(
        _get_file_data(
            bucket_name=BUCKET, key=s3_join(observer.dir, "run.json")
        ).decode("utf-8")
    )
    assert run["status"] == "COMPLETED"


@moto.mock_s3
def test_interrupted_event_updates_run_json(observer, sample_run):
    observer.started_event(**sample_run)
    run = json.loads(
        _get_file_data(
            bucket_name=BUCKET, key=s3_join(observer.dir, "run.json")
        ).decode("utf-8")
    )
    assert run["status"] == "RUNNING"
    observer.interrupted_event(T2, "SERVER_EXPLODED")
    run = json.loads(
        _get_file_data(
            bucket_name=BUCKET, key=s3_join(observer.dir, "run.json")
        ).decode("utf-8")
    )
    assert run["status"] == "SERVER_EXPLODED"


@moto.mock_s3
def test_failed_event_updates_run_json(observer, sample_run):
    observer.started_event(**sample_run)
    run = json.loads(
        _get_file_data(
            bucket_name=BUCKET, key=s3_join(observer.dir, "run.json")
        ).decode("utf-8")
    )
    assert run["status"] == "RUNNING"
    observer.failed_event(T2, "Everything imaginable went wrong")
    run = json.loads(
        _get_file_data(
            bucket_name=BUCKET, key=s3_join(observer.dir, "run.json")
        ).decode("utf-8")
    )
    assert run["status"] == "FAILED"


@moto.mock_s3
def test_queued_event_updates_run_json(observer, sample_run):
    del sample_run["start_time"]
    sample_run["queue_time"] = T2
    observer.queued_event(**sample_run)
    run = json.loads(
        _get_file_data(
            bucket_name=BUCKET, key=s3_join(observer.dir, "run.json")
        ).decode("utf-8")
    )
    assert run["status"] == "QUEUED"


@moto.mock_s3
def test_artifact_event_works(observer, sample_run, tmpfile):
    observer.started_event(**sample_run)
    observer.artifact_event("test_artifact.py", tmpfile.name)

    assert _key_exists(
        bucket_name=BUCKET, key=s3_join(observer.dir, "test_artifact.py")
    )
    artifact_data = _get_file_data(
        bucket_name=BUCKET, key=s3_join(observer.dir, "test_artifact.py")
    ).decode("utf-8")
    assert artifact_data == tmpfile.content


test_buckets = [
    ("hi", True),
    ("this_bucket_is_invalid", True),
    ("this-bucket-is-valid", False),
    ("this-bucket.is-valid", False),
    ("this-bucket..is-invalid", True),
]


@pytest.mark.parametrize("bucket_name, should_raise", test_buckets)
def test_raises_error_on_invalid_bucket_name(bucket_name, should_raise):
    if should_raise:
        with pytest.raises(ValueError):
            _ = S3Observer(bucket=bucket_name, basedir=BASEDIR, region=REGION)
    else:
        _ = S3Observer(bucket=bucket_name, basedir=BASEDIR, region=REGION)
