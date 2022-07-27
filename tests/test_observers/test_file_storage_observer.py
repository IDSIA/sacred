#!/usr/bin/env python
# coding=utf-8

import datetime
import os
from copy import copy
import pint
import pytest
import json
from pathlib import Path

from sacred.observers.file_storage import FileStorageObserver
from sacred.metrics_logger import ScalarMetricLogEntry, linearize_metrics


T1 = datetime.datetime(1999, 5, 4, 3, 2, 1, 0)
T2 = datetime.datetime(1999, 5, 5, 5, 5, 5, 5)


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


@pytest.fixture()
def dir_obs(tmpdir):
    basedir = tmpdir.join("file_storage")
    return basedir, FileStorageObserver(basedir.strpath)


def test_fs_observer_create_does_not_create_basedir(dir_obs):
    basedir, obs = dir_obs
    assert not basedir.exists()


def test_fs_observer_queued_event_creates_rundir(dir_obs, sample_run):
    basedir, obs = dir_obs
    _id = obs.queued_event(
        sample_run["ex_info"],
        sample_run["command"],
        sample_run["host_info"],
        datetime.datetime.utcnow(),
        sample_run["config"],
        sample_run["meta_info"],
        sample_run["_id"],
    )

    assert _id is not None
    run_dir = basedir.join(str(_id))
    assert run_dir.exists()
    config = json.loads(run_dir.join("config.json").read())
    assert config == sample_run["config"]

    run = json.loads(run_dir.join("run.json").read())
    assert run == {
        "experiment": sample_run["ex_info"],
        "command": sample_run["command"],
        "host": sample_run["host_info"],
        "meta": sample_run["meta_info"],
        "status": "QUEUED",
    }


def test_fs_observer_started_event_creates_rundir(dir_obs, sample_run):
    basedir, obs = dir_obs
    sample_run["_id"] = None
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(str(_id))
    assert run_dir.exists()
    assert run_dir.join("cout.txt").exists()
    config = json.loads(run_dir.join("config.json").read())
    assert config == sample_run["config"]

    run = json.loads(run_dir.join("run.json").read())
    assert run == {
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


def test_fs_observer_started_event_creates_rundir_with_filesystem_delay(
    dir_obs, sample_run, monkeypatch
):
    """Assumes listdir doesn't show existing file (e.g. due to caching or delay of network storage)"""
    basedir, obs = dir_obs
    sample_run["_id"] = None
    _id = obs.started_event(**sample_run)
    assert _id == "1"
    assert os.listdir(str(basedir)) == [_id]
    with monkeypatch.context() as m:
        m.setattr("os.listdir", lambda _: [])
        assert os.listdir(str(basedir)) == []
        _id2 = obs.started_event(**sample_run)
        assert _id2 == "2"


def test_fs_observer_started_event_raises_file_exists_error(
    dir_obs, sample_run, monkeypatch
):
    """Assumes some problem with the filesystem exists
    therefore run dir creation should stop after some re-tries
    """

    def mkdir_raises_file_exists(name, mode=0o777):
        raise FileExistsError("File already exists: " + name)

    basedir, obs = dir_obs
    sample_run["_id"] = None
    with monkeypatch.context() as m:
        m.setattr("os.mkdir", mkdir_raises_file_exists)
        with pytest.raises(FileExistsError):
            obs.started_event(**sample_run)


def test_fs_observer_started_event_stores_source(dir_obs, sample_run, tmpfile):
    basedir, obs = dir_obs
    sample_run["ex_info"]["sources"] = [[tmpfile.name, tmpfile.md5sum]]

    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)

    assert run_dir.exists()
    run = json.loads(run_dir.join("run.json").read())
    ex_info = copy(run["experiment"])
    assert ex_info["sources"][0][0] == tmpfile.name
    source_path = ex_info["sources"][0][1]
    source = basedir.join(source_path)
    assert source.exists()
    assert source.read() == "import sacred\n"


def test_fs_observer_started_event_uses_given_id(dir_obs, sample_run):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    assert _id == sample_run["_id"]
    assert basedir.join(_id).exists()


def test_fs_observer_heartbeat_event_updates_run(dir_obs, sample_run):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)
    info = {"my_info": [1, 2, 3], "nr": 7}
    obs.heartbeat_event(info=info, captured_out="some output", beat_time=T2, result=17)

    assert run_dir.join("cout.txt").read() == "some output"
    run = json.loads(run_dir.join("run.json").read())

    assert run["heartbeat"] == T2.isoformat()
    assert run["result"] == 17

    assert run_dir.join("info.json").exists()
    i = json.loads(run_dir.join("info.json").read())
    assert info == i


def test_fs_observer_heartbeat_event_multiple_updates_run(dir_obs, sample_run):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)
    info = {"my_info": [1, 2, 3], "nr": 7}

    captured_outs = [("some output %d\n" % i) for i in range(10)]
    beat_times = [(T2 + datetime.timedelta(seconds=i * 10)) for i in range(10)]

    for idx in range(len(beat_times)):
        expected_captured_output = (
            "\n".join([x.strip() for x in captured_outs[: (idx + 1)]]) + "\n"
        )
        obs.heartbeat_event(
            info=info,
            captured_out=expected_captured_output,
            beat_time=beat_times[idx],
            result=17,
        )

        assert run_dir.join("cout.txt").read() == expected_captured_output
        run = json.loads(run_dir.join("run.json").read())

        assert run["heartbeat"] == beat_times[idx].isoformat()
        assert run["result"] == 17

        assert run_dir.join("info.json").exists()
        i = json.loads(run_dir.join("info.json").read())
        assert info == i


def test_fs_observer_completed_event_updates_run(dir_obs, sample_run):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)

    obs.completed_event(stop_time=T2, result=42)

    run = json.loads(run_dir.join("run.json").read())
    assert run["stop_time"] == T2.isoformat()
    assert run["status"] == "COMPLETED"
    assert run["result"] == 42


def test_fs_observer_interrupted_event_updates_run(dir_obs, sample_run):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)

    obs.interrupted_event(interrupt_time=T2, status="CUSTOM_INTERRUPTION")

    run = json.loads(run_dir.join("run.json").read())
    assert run["stop_time"] == T2.isoformat()
    assert run["status"] == "CUSTOM_INTERRUPTION"


def test_fs_observer_failed_event_updates_run(dir_obs, sample_run):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)

    fail_trace = "lots of errors and\nso\non..."
    obs.failed_event(fail_time=T2, fail_trace=fail_trace)

    run = json.loads(run_dir.join("run.json").read())
    assert run["stop_time"] == T2.isoformat()
    assert run["status"] == "FAILED"
    assert run["fail_trace"] == fail_trace


def test_fs_observer_artifact_event(dir_obs, sample_run, tmpfile):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)

    obs.artifact_event("my_artifact.py", tmpfile.name)

    artifact = run_dir.join("my_artifact.py")
    assert artifact.exists()
    assert artifact.read() == tmpfile.content

    run = json.loads(run_dir.join("run.json").read())
    assert len(run["artifacts"]) == 1
    assert run["artifacts"][0] == artifact.relto(run_dir)


def test_fs_observer_resource_event(dir_obs, sample_run, tmpfile):
    basedir, obs = dir_obs
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(_id)

    obs.resource_event(tmpfile.name)

    res_dir = basedir.join("_resources")
    assert res_dir.exists()
    assert len(res_dir.listdir()) == 1
    assert res_dir.listdir()[0].read() == tmpfile.content

    run = json.loads(run_dir.join("run.json").read())
    assert len(run["resources"]) == 1
    assert run["resources"][0] == [tmpfile.name, res_dir.listdir()[0].strpath]


def test_fs_observer_resource_event_does_not_duplicate(dir_obs, sample_run, tmpfile):
    basedir, obs = dir_obs
    obs2 = FileStorageObserver(obs.basedir)
    obs.started_event(**sample_run)

    obs.resource_event(tmpfile.name)
    # let's have another run from a different observer
    sample_run["_id"] = None
    _id = obs2.started_event(**sample_run)
    run_dir = basedir.join(str(_id))
    obs2.resource_event(tmpfile.name)

    res_dir = basedir.join("_resources")
    assert res_dir.exists()
    assert len(res_dir.listdir()) == 1
    assert res_dir.listdir()[0].read() == tmpfile.content

    run = json.loads(run_dir.join("run.json").read())
    assert len(run["resources"]) == 1
    assert run["resources"][0] == [tmpfile.name, res_dir.listdir()[0].strpath]


def test_fs_observer_equality(dir_obs):
    basedir, obs = dir_obs
    obs2 = FileStorageObserver(obs.basedir)
    assert obs == obs2
    assert not obs != obs2

    assert not obs == "foo"
    assert obs != "foo"


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


def test_log_metrics(dir_obs, sample_run, logged_metrics):
    """Test storing of scalar measurements.

    Test whether measurements logged using _run.metrics.log_scalar_metric
    are being stored in the metrics.json file.

    Metrics are stored as a json with each metric indexed by a name
    (e.g.: 'training.loss'). Each metric for the given name is then
    stored as three lists: iteration step(steps), the values logged(values)
    and the timestamp at which the measurement was taken(timestamps)
    """

    # Start the experiment
    basedir, obs = dir_obs
    sample_run["_id"] = None
    _id = obs.started_event(**sample_run)
    run_dir = basedir.join(str(_id))

    # Initialize the info dictionary and standard output with arbitrary values
    info = {"my_info": [1, 2, 3], "nr": 7}
    outp = "some output"

    obs.log_metrics(linearize_metrics(logged_metrics[:6]), info)
    obs.heartbeat_event(info=info, captured_out=outp, beat_time=T1, result=0)

    assert run_dir.join("metrics.json").exists()
    metrics = json.loads(run_dir.join("metrics.json").read())

    # Confirm that we have only two metric names registered.
    # and they have all the information we need.
    assert len(metrics) == 2
    assert "training.loss" in metrics
    assert "training.accuracy" in metrics
    for v in ["steps", "values", "timestamps"]:
        assert v in metrics["training.loss"]
        assert v in metrics["training.accuracy"]

    # Verify they have all the information
    # we logged in the right order.
    loss = metrics["training.loss"]
    assert loss["steps"] == [10, 20, 30]
    assert loss["values"] == [1, 2, 3]
    for i in range(len(loss["timestamps"]) - 1):
        assert loss["timestamps"][i] <= loss["timestamps"][i + 1]

    accuracy = metrics["training.accuracy"]
    assert accuracy["steps"] == [10, 20, 30]
    assert accuracy["values"] == [100, 200, 300]

    # Now, process the remaining events
    # The metrics shouldn't be overwritten, but appended instead.
    obs.log_metrics(linearize_metrics(logged_metrics[6:]), info)
    obs.heartbeat_event(info=info, captured_out=outp, beat_time=T2, result=0)

    # Reload the new metrics
    metrics = json.loads(run_dir.join("metrics.json").read())

    # The newly added metrics belong to the same run and have the same names,
    # so the total number of metrics should not change.
    assert len(metrics) == 2

    assert "training.loss" in metrics
    loss = metrics["training.loss"]
    assert loss["steps"] == [10, 20, 30, 40, 50, 60]
    assert loss["values"] == [1, 2, 3, 10, 20, 30]
    for i in range(len(loss["timestamps"]) - 1):
        assert loss["timestamps"][i] <= loss["timestamps"][i + 1]

    # Read the training.accuracy metric and verify it's unchanged
    assert "training.accuracy" in metrics
    accuracy = metrics["training.accuracy"]
    assert accuracy["steps"] == [10, 20, 30]
    assert accuracy["values"] == [100, 200, 300]

    # Attempt to insert a metric with units
    obs.log_metrics(
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
    obs.heartbeat_event(info=info, captured_out=outp, beat_time=T1, result=0)
    # Reload the new metrics
    metrics = json.loads(run_dir.join("metrics.json").read())
    assert metrics["training.units"]["values"][0] == 1
    assert metrics["training.units"]["units"] == "meter"


def test_observer_equality(tmpdir):
    observer_1 = FileStorageObserver(str(tmpdir / "a"))
    observer_2 = FileStorageObserver(str(tmpdir / "b"))
    observer_3 = FileStorageObserver(str(tmpdir / "a"))
    assert observer_1 == observer_3
    assert observer_1 != observer_2


def test_blacklist_paths(tmpdir, dir_obs, sample_run):
    basedir, obs = dir_obs
    obs.started_event(**sample_run)
    other_file = Path(str(tmpdir / "dodo.txt"))
    other_file.touch()
    with pytest.raises(FileExistsError):
        obs.save_file(str(other_file), "cout.txt")


def test_no_duplicate(tmpdir, sample_run):
    obs = FileStorageObserver(tmpdir, copy_artifacts=False)
    file = Path(str(tmpdir / "koko.txt"))
    file.touch()
    obs.started_event(**sample_run)
    obs.resource_event(str(file))
    assert not os.path.exists(tmpdir / "_resources")

    # Test the test: that the resource would otherwise have been created.
    obs = FileStorageObserver(tmpdir, copy_artifacts=True)
    sample_run["_id"] = sample_run["_id"] + "_2"
    obs.started_event(**sample_run)
    obs.resource_event(str(file))
    assert os.path.exists(tmpdir / "_resources")
    assert any(x.startswith("koko") for x in os.listdir(tmpdir / "_resources"))


def test_no_sources(tmpdir, tmpfile, sample_run):
    obs = FileStorageObserver(tmpdir, copy_sources=False)
    sample_run["ex_info"]["sources"] = [[tmpfile.name, tmpfile.md5sum]]
    obs.started_event(**sample_run)
    assert not os.path.exists(tmpdir / "_sources")

    # Test the test: that the source would otherwise have been created.
    obs = FileStorageObserver(tmpdir, copy_sources=True)
    sample_run["_id"] = sample_run["_id"] + "_2"
    obs.started_event(**sample_run)
    name, _ = os.path.splitext(os.path.basename(tmpfile.name))
    assert os.path.exists(tmpdir / "_sources")
    assert any(x.startswith(name) for x in os.listdir(tmpdir / "_sources"))
