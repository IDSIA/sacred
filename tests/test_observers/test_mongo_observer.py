import datetime
import os
import sys
from glob import glob

import mock
import pint
import pytest

if sys.version_info >= (3, 10):
    pytest.skip(
        "Skip pymongo tests for Python 3.10 because mongomock doesn't "
        "support Python 3.10",
        allow_module_level=True,
    )

from sacred.metrics_logger import ScalarMetricLogEntry, linearize_metrics

pymongo = pytest.importorskip("pymongo")
mongomock = pytest.importorskip("mongomock")

import gridfs
from mongomock.gridfs import enable_gridfs_integration

enable_gridfs_integration()
from .failing_mongo_mock import FailingMongoClient

from sacred.dependencies import get_digest
from sacred.observers.mongo import MongoObserver, force_bson_encodeable

T1 = datetime.datetime(1999, 5, 4, 3, 2, 1)
T2 = datetime.datetime(1999, 5, 5, 5, 5, 5)
T3 = datetime.datetime(1999, 5, 5, 5, 10, 5)


def test_create_should_raise_error_on_non_pymongo_client():
    client = mongomock.MongoClient()
    with pytest.raises(ValueError):
        MongoObserver(client=client)


def test_create_should_raise_error_on_both_client_and_url():
    real_client = pymongo.MongoClient()
    with pytest.raises(ValueError, match="Cannot pass both a client and a url."):
        MongoObserver(client=real_client, url="mymongourl")


def test_create_should_raise_error_on_both_prefix_and_runs():
    real_client = pymongo.MongoClient()
    with pytest.raises(
        ValueError, match="Cannot pass both collection and a collection prefix."
    ):
        MongoObserver(
            client=real_client,
            collection_prefix="myprefix",
            collection="some_collection",
        )


@pytest.fixture
def mongo_obs():
    db = mongomock.MongoClient().db
    runs = db.runs
    metrics = db.metrics
    fs = gridfs.GridFS(db)
    return MongoObserver.create_from(runs, fs, metrics_collection=metrics)


@pytest.fixture
def mongo_obs_with_prefix():
    # create a mongo observer with a collection prefix
    real_client = pymongo.MongoClient()
    return MongoObserver(collection_prefix="testing", client=real_client)


@pytest.fixture
def mongo_obs_without_prefix():
    # create a mongo observer without a collection prefix
    # i.e. should default to collections 'runs' and 'metrics'
    real_client = pymongo.MongoClient()
    return MongoObserver(client=real_client)


@pytest.fixture
def mongo_obs_with_collection():
    # old, deprecated way of creating a mongo observer
    # should use 'my_collection' for runs and 'metrics' for metrics
    real_client = pymongo.MongoClient()
    return MongoObserver(client=real_client, collection="my_collection")


@pytest.fixture
def failing_mongo_observer():
    db = FailingMongoClient(
        max_calls_before_failure=2,
        exception_to_raise=pymongo.errors.ServerSelectionTimeoutError,
    ).db

    runs = db.runs
    metrics = db.metrics
    fs = gridfs.GridFS(db)
    return MongoObserver.create_from(runs, fs, metrics_collection=metrics)


@pytest.fixture()
def sample_run():
    exp = {"name": "test_exp", "sources": [], "doc": "", "base_dir": "/tmp"}
    host = {"hostname": "test_host", "cpu_count": 1, "python_version": "3.4"}
    config = {"config": "True", "foo": "bar", "answer": 42}
    command = "run"
    meta_info = {"comment": "test run"}
    return {
        "_id": "FEDCBA9876543210",
        "ex_info": exp,
        "command": command,
        "host_info": host,
        "start_time": T1,
        "config": config,
        "meta_info": meta_info,
    }


def test_mongo_observer_started_event_creates_run(mongo_obs, sample_run):
    sample_run["_id"] = None
    _id = mongo_obs.started_event(**sample_run)
    assert _id is not None
    assert mongo_obs.runs.count_documents({}) == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run == {
        "_id": _id,
        "experiment": sample_run["ex_info"],
        "format": mongo_obs.VERSION,
        "command": sample_run["command"],
        "host": sample_run["host_info"],
        "start_time": sample_run["start_time"],
        "heartbeat": None,
        "info": {},
        "captured_out": "",
        "artifacts": [],
        "config": sample_run["config"],
        "meta": sample_run["meta_info"],
        "status": "RUNNING",
        "resources": [],
    }


def test_mongo_observer_started_event_uses_given_id(mongo_obs, sample_run):
    _id = mongo_obs.started_event(**sample_run)
    assert _id == sample_run["_id"]
    assert mongo_obs.runs.count_documents({}) == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run["_id"] == sample_run["_id"]


def test_mongo_observer_equality(mongo_obs):
    runs = mongo_obs.runs
    fs = mock.MagicMock()
    m = MongoObserver.create_from(runs, fs)
    assert mongo_obs == m
    assert not mongo_obs != m

    assert not mongo_obs == "foo"
    assert mongo_obs != "foo"


def test_mongo_observer_heartbeat_event_updates_run(mongo_obs, sample_run):
    mongo_obs.started_event(**sample_run)

    info = {"my_info": [1, 2, 3], "nr": 7}
    outp = "some output"
    mongo_obs.heartbeat_event(info=info, captured_out=outp, beat_time=T2, result=1337)

    assert mongo_obs.runs.count_documents({}) == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run["heartbeat"] == T2
    assert db_run["result"] == 1337
    assert db_run["info"] == info
    assert db_run["captured_out"] == outp


def test_mongo_observer_fails(failing_mongo_observer, sample_run):
    failing_mongo_observer.started_event(**sample_run)

    info = {"my_info": [1, 2, 3], "nr": 7}
    outp = "some output"
    failing_mongo_observer.heartbeat_event(
        info=info, captured_out=outp, beat_time=T2, result=1337
    )

    with pytest.raises(pymongo.errors.ConnectionFailure):
        failing_mongo_observer.heartbeat_event(
            info=info, captured_out=outp, beat_time=T3, result=1337
        )


def test_mongo_observer_saves_after_failure(failing_mongo_observer, sample_run):
    failure_dir = "/tmp/my_failure/dir"
    failing_mongo_observer.failure_dir = failure_dir
    failing_mongo_observer.started_event(**sample_run)

    info = {"my_info": [1, 2, 3], "nr": 7}
    outp = "some output"
    failing_mongo_observer.heartbeat_event(
        info=info, captured_out=outp, beat_time=T2, result=1337
    )

    failing_mongo_observer.completed_event(stop_time=T3, result=42)
    glob_pattern = "{}/sacred_mongo_fail_{}*.pickle".format(
        failure_dir, sample_run["_id"]
    )
    os.path.isfile(glob(glob_pattern)[-1])


def test_mongo_observer_completed_event_updates_run(mongo_obs, sample_run):
    mongo_obs.started_event(**sample_run)

    mongo_obs.completed_event(stop_time=T2, result=42)

    assert mongo_obs.runs.count_documents({}) == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run["stop_time"] == T2
    assert db_run["result"] == 42
    assert db_run["status"] == "COMPLETED"


def test_mongo_observer_interrupted_event_updates_run(mongo_obs, sample_run):
    mongo_obs.started_event(**sample_run)

    mongo_obs.interrupted_event(interrupt_time=T2, status="INTERRUPTED")

    assert mongo_obs.runs.count_documents({}) == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run["stop_time"] == T2
    assert db_run["status"] == "INTERRUPTED"


def test_mongo_observer_failed_event_updates_run(mongo_obs, sample_run):
    mongo_obs.started_event(**sample_run)

    fail_trace = "lots of errors and\nso\non..."
    mongo_obs.failed_event(fail_time=T2, fail_trace=fail_trace)

    assert mongo_obs.runs.count_documents({}) == 1
    db_run = mongo_obs.runs.find_one()
    assert db_run["stop_time"] == T2
    assert db_run["status"] == "FAILED"
    assert db_run["fail_trace"] == fail_trace


def test_mongo_observer_artifact_event(mongo_obs, sample_run):
    mongo_obs.started_event(**sample_run)

    filename = "setup.py"
    name = "mysetup"

    mongo_obs.artifact_event(name, filename)

    [file] = mongo_obs.fs.list()
    assert file.endswith(name)

    db_run = mongo_obs.runs.find_one()
    assert db_run["artifacts"]


def test_mongo_observer_resource_event(mongo_obs, sample_run):
    mongo_obs.started_event(**sample_run)

    filename = "setup.py"
    md5 = get_digest(filename)

    mongo_obs.resource_event(filename)

    db_run = mongo_obs.runs.find_one()
    assert db_run["resources"] == [[filename, md5]]


def test_force_bson_encodable_doesnt_change_valid_document():
    d = {
        "int": 1,
        "string": "foo",
        "float": 23.87,
        "list": ["a", 1, True],
        "bool": True,
        "cr4zy: _but_ [legal) Key!": "$illegal.key.as.value",
        "datetime": datetime.datetime.utcnow(),
        "tuple": (1, 2.0, "three"),
        "none": None,
    }
    assert force_bson_encodeable(d) == d


def test_force_bson_encodable_substitutes_illegal_value_with_strings():
    d = {
        "a_module": datetime,
        "some_legal_stuff": {"foo": "bar", "baz": [1, 23, 4]},
        "nested": {"dict": {"with": {"illegal_module": mock}}},
        "$illegal": "because it starts with a $",
        "il.legal": "because it contains a .",
        12.7: "illegal because it is not a string key",
    }
    expected = {
        "a_module": str(datetime),
        "some_legal_stuff": {"foo": "bar", "baz": [1, 23, 4]},
        "nested": {"dict": {"with": {"illegal_module": str(mock)}}},
        "@illegal": "because it starts with a $",
        "il,legal": "because it contains a .",
        "12,7": "illegal because it is not a string key",
    }
    assert force_bson_encodeable(d) == expected


@pytest.fixture
def logged_metrics():
    return [
        ScalarMetricLogEntry("training.loss", 10, datetime.datetime.utcnow(), 1),
        ScalarMetricLogEntry("training.loss", 20, datetime.datetime.utcnow(), 2),
        ScalarMetricLogEntry("training.loss", 30, datetime.datetime.utcnow(), 3),
        ScalarMetricLogEntry("training.accuracy", 10, datetime.datetime.utcnow(), 100),
        ScalarMetricLogEntry("training.accuracy", 20, datetime.datetime.utcnow(), 200),
        ScalarMetricLogEntry("training.accuracy", 30, datetime.datetime.utcnow(), 300),
        ScalarMetricLogEntry("training.loss", 40, datetime.datetime.utcnow(), 10),
        ScalarMetricLogEntry("training.loss", 50, datetime.datetime.utcnow(), 20),
        ScalarMetricLogEntry("training.loss", 60, datetime.datetime.utcnow(), 30),
    ]


def test_log_metrics(mongo_obs, sample_run, logged_metrics):
    """
    Test storing scalar measurements

    Test whether measurements logged using _run.metrics.log_scalar_metric
    are being stored in the 'metrics' collection
    and that the experiment 'info' dictionary contains a valid reference
    to the metrics collection for each of the metric.

    Metrics are identified by name (e.g.: 'training.loss') and by the
    experiment run that produced them. Each metric contains a list of x values
    (e.g. iteration step), y values (measured values) and timestamps of when
    each of the measurements was taken.
    """

    # Start the experiment
    mongo_obs.started_event(**sample_run)

    # Initialize the info dictionary and standard output with arbitrary values
    info = {"my_info": [1, 2, 3], "nr": 7}
    outp = "some output"

    # Take first 6 measured events, group them by metric name
    # and store the measured series to the 'metrics' collection
    # and reference the newly created records in the 'info' dictionary.
    mongo_obs.log_metrics(linearize_metrics(logged_metrics[:6]), info)
    # Call standard heartbeat event (store the info dictionary to the database)
    mongo_obs.heartbeat_event(info=info, captured_out=outp, beat_time=T1, result=0)

    # There should be only one run stored
    assert mongo_obs.runs.count_documents({}) == 1
    db_run = mongo_obs.runs.find_one()
    # ... and the info dictionary should contain a list of created metrics
    assert "metrics" in db_run["info"]
    assert type(db_run["info"]["metrics"]) == list

    # The metrics, stored in the metrics collection,
    # should be two (training.loss and training.accuracy)
    assert mongo_obs.metrics.count_documents({}) == 2
    # Read the training.loss metric and make sure it references the correct run
    # and that the run (in the info dictionary) references the correct metric record.
    loss = mongo_obs.metrics.find_one(
        {"name": "training.loss", "run_id": db_run["_id"]}
    )
    assert {"name": "training.loss", "id": str(loss["_id"])} in db_run["info"][
        "metrics"
    ]
    assert loss["steps"] == [10, 20, 30]
    assert loss["values"] == [1, 2, 3]
    for i in range(len(loss["timestamps"]) - 1):
        assert loss["timestamps"][i] <= loss["timestamps"][i + 1]

    # Read the training.accuracy metric and check the references as with the training.loss above
    accuracy = mongo_obs.metrics.find_one(
        {"name": "training.accuracy", "run_id": db_run["_id"]}
    )
    assert {"name": "training.accuracy", "id": str(accuracy["_id"])} in db_run["info"][
        "metrics"
    ]
    assert accuracy["steps"] == [10, 20, 30]
    assert accuracy["values"] == [100, 200, 300]

    # Now, process the remaining events
    # The metrics shouldn't be overwritten, but appended instead.
    mongo_obs.log_metrics(linearize_metrics(logged_metrics[6:]), info)
    mongo_obs.heartbeat_event(info=info, captured_out=outp, beat_time=T2, result=0)

    assert mongo_obs.runs.count_documents({}) == 1
    db_run = mongo_obs.runs.find_one()
    assert "metrics" in db_run["info"]

    # The newly added metrics belong to the same run and have the same names, so the total number
    # of metrics should not change.
    assert mongo_obs.metrics.count_documents({}) == 2
    loss = mongo_obs.metrics.find_one(
        {"name": "training.loss", "run_id": db_run["_id"]}
    )
    assert {"name": "training.loss", "id": str(loss["_id"])} in db_run["info"][
        "metrics"
    ]
    # ... but the values should be appended to the original list
    assert loss["steps"] == [10, 20, 30, 40, 50, 60]
    assert loss["values"] == [1, 2, 3, 10, 20, 30]
    for i in range(len(loss["timestamps"]) - 1):
        assert loss["timestamps"][i] <= loss["timestamps"][i + 1]

    accuracy = mongo_obs.metrics.find_one(
        {"name": "training.accuracy", "run_id": db_run["_id"]}
    )
    assert {"name": "training.accuracy", "id": str(accuracy["_id"])} in db_run["info"][
        "metrics"
    ]
    assert accuracy["steps"] == [10, 20, 30]
    assert accuracy["values"] == [100, 200, 300]

    # Make sure that when starting a new experiment, new records in metrics are created
    # instead of appending to the old ones.
    sample_run["_id"] = "NEWID"
    # Start the experiment
    mongo_obs.started_event(**sample_run)
    mongo_obs.log_metrics(linearize_metrics(logged_metrics[:4]), info)
    mongo_obs.heartbeat_event(info=info, captured_out=outp, beat_time=T1, result=0)
    # A new run has been created
    assert mongo_obs.runs.count_documents({}) == 2
    # Another 2 metrics have been created
    assert mongo_obs.metrics.count_documents({}) == 4
    db_run = mongo_obs.runs.find_one({"_id": "NEWID"})

    # Attempt to insert a metric with units
    mongo_obs.log_metrics(
        linearize_metrics(
            [
                ScalarMetricLogEntry(
                    "training.units",
                    1,
                    datetime.datetime.utcnow(),
                    pint.Quantity(1, "meter"),
                )
            ]
        ),
        info,
    )
    mongo_obs.heartbeat_event(info=info, captured_out=outp, beat_time=T1, result=0)
    units = mongo_obs.metrics.find_one(
        {"name": "training.units", "run_id": db_run["_id"]}
    )
    assert units["values"][0] == 1
    assert units["units"] == "meter"


def test_mongo_observer_artifact_event_content_type_added(mongo_obs, sample_run):
    """Test that the detected content_type is added to other metadata."""
    mongo_obs.started_event(**sample_run)

    filename = "setup.py"
    name = "mysetup"

    mongo_obs.artifact_event(name, filename)

    file = mongo_obs.fs.find_one({})
    assert file.content_type == "text/x-python"

    db_run = mongo_obs.runs.find_one()
    assert db_run["artifacts"]


def test_mongo_observer_artifact_event_content_type_not_overwritten(
    mongo_obs, sample_run
):
    """Test that manually set content_type is not overwritten by automatic detection."""
    mongo_obs.started_event(**sample_run)

    filename = "setup.py"
    name = "mysetup"

    mongo_obs.artifact_event(name, filename, content_type="application/json")

    file = mongo_obs.fs.find_one({})
    assert file.content_type == "application/json"

    db_run = mongo_obs.runs.find_one()
    assert db_run["artifacts"]


def test_mongo_observer_artifact_event_metadata(mongo_obs, sample_run):
    """Test that the detected content-type is added to other metadata."""
    mongo_obs.started_event(**sample_run)

    filename = "setup.py"
    name = "mysetup"

    mongo_obs.artifact_event(name, filename, metadata={"comment": "the setup file"})

    file = mongo_obs.fs.find_one({})
    assert file.metadata["comment"] == "the setup file"

    db_run = mongo_obs.runs.find_one()
    assert db_run["artifacts"]


def test_mongo_observer_created_with_prefix(mongo_obs_with_prefix):
    print("with_prefix_test")
    runs_collection = mongo_obs_with_prefix.runs
    metrics_collection = mongo_obs_with_prefix.metrics
    assert runs_collection.name == "testing_runs"
    assert metrics_collection.name == "testing_metrics"


def test_mongo_observer_created_without_prefix(mongo_obs_without_prefix):
    print("without_prefix_test")
    runs_collection = mongo_obs_without_prefix.runs
    metrics_collection = mongo_obs_without_prefix.metrics
    assert runs_collection.name == "runs"
    assert metrics_collection.name == "metrics"


def test_mongo_observer_created_with_collection(mongo_obs_with_collection):
    print("with_collection_test")
    runs_collection = mongo_obs_with_collection.runs
    metrics_collection = mongo_obs_with_collection.metrics
    assert runs_collection.name == "my_collection"
    assert metrics_collection.name == "metrics"
