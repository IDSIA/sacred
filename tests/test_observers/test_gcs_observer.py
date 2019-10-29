import pytest
import datetime
import os
import json

from sacred.observers import GoogleCloudStorageObserver

storage = pytest.importorskip("google.cloud.storage")

T1 = datetime.datetime(1999, 5, 4, 3, 2, 1, 0)
T2 = datetime.datetime(1999, 5, 5, 5, 5, 5, 5)

try:
    BUCKET = os.environ["CLOUD_STORAGE_BUCKET"]
    _CREDENTIALS = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
except KeyError as key:
    print("Skipping test due to missing environment variable", key)
    pytest.skip("skipping google authentication-only tests", allow_module_level=True)

BASEDIR = "sacred-tests"


def gcs_join(*args):
    return "/".join(args)


def _delete_bucket_directory(bucket, basedir):
    blobs = bucket.list_blobs(prefix=basedir)
    for blob in blobs:
        blob.delete()


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
def observer(basedir=None):
    if basedir is None:
        basedir = BASEDIR

    _observer = GoogleCloudStorageObserver(bucket=BUCKET, basedir=basedir)

    yield _observer

    # Make sure to delete directory afterwards
    _delete_bucket_directory(_observer.bucket, basedir)


def _get_blob(bucket, directory, filename):
    prefixed_blobs = [blob for blob in bucket.list_blobs(prefix=directory)]
    file_blob = next((blob for blob in prefixed_blobs if filename in blob.name))
    return file_blob


def _bucket_exists(bucket):
    all_blobs = [blob for blob in bucket.list_blobs()]
    return len(all_blobs) > 0


def _file_exists(bucket, directory, filename):
    file_blob = _get_blob(bucket, directory, filename)
    return gcs_join(directory, filename) == file_blob.name


def _get_file_data(bucket, directory, filename):
    file_blob = _get_blob(bucket, directory, filename)
    return file_blob.download_as_string()


def test_gcs_observer_started_event_creates_bucket(observer, sample_run):
    bucket = observer.bucket
    _id = observer.started_event(**sample_run)
    run_dir = gcs_join(BASEDIR, str(_id))

    assert _bucket_exists(bucket)
    assert _file_exists(bucket, run_dir, filename="cout.txt")
    assert _file_exists(bucket, run_dir, filename="config.json")
    assert _file_exists(bucket, run_dir, filename="run.json")

    config = _get_file_data(bucket, run_dir, filename="config.json")
    assert json.loads(config.decode("utf-8")) == sample_run["config"]

    run = _get_file_data(bucket, run_dir, filename="run.json")
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


def test_gcs_observer_started_event_increments_run_id(observer, sample_run):
    _id = observer.started_event(**sample_run)
    _id2 = observer.started_event(**sample_run)
    assert _id + 1 == _id2


def test_gcs_observer_equality():
    obs_one = GoogleCloudStorageObserver(bucket=BUCKET, basedir=BASEDIR)
    obs_two = GoogleCloudStorageObserver(bucket=BUCKET, basedir=BASEDIR)
    assert obs_one == obs_two

    test_directory = "sacred-tests-2/dir"
    different_basedir = GoogleCloudStorageObserver(
        bucket=BUCKET, basedir=test_directory
    )
    assert obs_one != different_basedir

    _delete_bucket_directory(obs_one.bucket, BASEDIR)
    _delete_bucket_directory(different_basedir.bucket, test_directory)


def test_raises_error_on_duplicate_id_directory(observer, sample_run):
    observer.started_event(**sample_run)
    sample_run["_id"] = 1
    with pytest.raises(FileExistsError):
        observer.started_event(**sample_run)


def test_completed_event_updates_run_json(observer, sample_run):
    observer.started_event(**sample_run)
    run = json.loads(
        _get_file_data(observer.bucket, observer.dir, filename="run.json").decode(
            "utf-8"
        )
    )
    assert run["status"] == "RUNNING"
    observer.completed_event(T2, "success!")
    run = json.loads(
        _get_file_data(observer.bucket, observer.dir, filename="run.json").decode(
            "utf-8"
        )
    )
    assert run["status"] == "COMPLETED"


def test_interrupted_event_updates_run_json(observer, sample_run):
    observer.started_event(**sample_run)
    run = json.loads(
        _get_file_data(observer.bucket, observer.dir, filename="run.json").decode(
            "utf-8"
        )
    )
    assert run["status"] == "RUNNING"
    observer.interrupted_event(T2, "SERVER_EXPLODED")
    run = json.loads(
        _get_file_data(observer.bucket, observer.dir, filename="run.json").decode(
            "utf-8"
        )
    )
    assert run["status"] == "SERVER_EXPLODED"


def test_failed_event_updates_run_json(observer, sample_run):
    observer.started_event(**sample_run)
    run = json.loads(
        _get_file_data(observer.bucket, observer.dir, "run.json").decode("utf-8")
    )
    assert run["status"] == "RUNNING"
    observer.failed_event(T2, "Everything imaginable went wrong")
    run = json.loads(
        _get_file_data(observer.bucket, observer.dir, "run.json").decode("utf-8")
    )
    assert run["status"] == "FAILED"


def test_queued_event_updates_run_json(observer, sample_run):
    del sample_run["start_time"]
    sample_run["queue_time"] = T2
    observer.queued_event(**sample_run)
    run = json.loads(
        _get_file_data(observer.bucket, observer.dir, "run.json").decode("utf-8")
    )
    assert run["status"] == "QUEUED"


def test_artifact_event_works(observer, sample_run, tmpfile):
    observer.started_event(**sample_run)
    observer.artifact_event("test_artifact.py", tmpfile.name)

    assert _file_exists(observer.bucket, observer.dir, "test_artifact.py")
    artifact_data = _get_file_data(
        observer.bucket, observer.dir, "test_artifact.py"
    ).decode("utf-8")
    assert artifact_data == tmpfile.content


@pytest.fixture
def valid_buckets():
    return [
        "this_bucket_is_valid",
        "th15_8uck3t_15_v4l1d",
        "this-bucket-is-valid",
        "this-bucket.is-valid",
    ]


@pytest.fixture
def invalid_buckets():
    return [
        "hi",
        "goog-24",
        "this-bucket..is-invalid",
        "-this-bucket-is-invalid",
        "this-BUCKET-is-invalid",
        "this-google-is-invalid",
        "this-g00gle-is-invalid",
        "192.168.5.4",
    ]


def test_does_not_raise_error_on_valid_bucket_name(valid_buckets):
    for bucket_name in valid_buckets:
        _ = GoogleCloudStorageObserver(bucket=bucket_name, basedir=BASEDIR)


def test_raises_error_on_invalid_bucket_name(invalid_buckets):
    for bucket_name in invalid_buckets:
        with pytest.raises(ValueError):
            _ = GoogleCloudStorageObserver(bucket=bucket_name, basedir=BASEDIR)
