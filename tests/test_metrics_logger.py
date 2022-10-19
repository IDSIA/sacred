#!/usr/bin/env python
# coding=utf-8

import datetime

import pytest
import sacred.optional as opt
from sacred import Experiment
from sacred.metrics_logger import (
    MetricLogEntry,
    MetricsLogger,
    ScalarMetricLogEntry,
    linearize_metrics,
)


@pytest.fixture()
def ex():
    return Experiment("Test experiment")


def test_log_scalar_metric_with_run(ex):
    START = 10
    END = 100
    STEP_SIZE = 5
    messages = {}

    @ex.main
    def main_function(_run):
        # First, make sure the queue is empty:
        assert len(ex.current_run._metrics.get_last_metrics()) == 0
        for i in range(START, END, STEP_SIZE):
            val = i * i
            _run.log_scalar("training.loss", val, i)
        messages["messages"] = ex.current_run._metrics.get_last_metrics()
        """Calling get_last_metrics clears the metrics logger internal queue.
        If we don't call it here, it would be called during Sacred heartbeat 
        event after the run finishes, and the data we want to test would 
        be lost."""

    ex.run()
    assert ex.current_run is not None
    messages = messages["messages"][0].entries
    assert len(messages) == (END - START) / STEP_SIZE
    for i in range(len(messages) - 1):
        assert messages[i].step < messages[i + 1].step
        assert messages[i].step == START + i * STEP_SIZE
        assert messages[i].timestamp <= messages[i + 1].timestamp


def test_log_scalar_metric_with_ex(ex):
    messages = {}
    START = 10
    END = 100
    STEP_SIZE = 5

    @ex.main
    def main_function(_run):
        for i in range(START, END, STEP_SIZE):
            val = i * i
            ex.log_scalar("training.loss", val, i)
        messages["messages"] = ex.current_run._metrics.get_last_metrics()

    ex.run()
    assert ex.current_run is not None
    messages = messages["messages"][0].entries
    assert len(messages) == (END - START) / STEP_SIZE
    for i in range(len(messages) - 1):
        assert messages[i].step < messages[i + 1].step
        assert messages[i].step == START + i * STEP_SIZE
        assert messages[i].timestamp <= messages[i + 1].timestamp


def test_log_scalar_metric_with_implicit_step(ex):
    messages = {}

    @ex.main
    def main_function(_run):
        for i in range(10):
            val = i * i
            ex.log_scalar("training.loss", val)
        messages["messages"] = ex.current_run._metrics.get_last_metrics()

    ex.run()
    assert ex.current_run is not None
    messages = messages["messages"][0].entries
    assert len(messages) == 10
    for i in range(len(messages) - 1):
        assert messages[i].step < messages[i + 1].step
        assert messages[i].step == i
        assert messages[i].timestamp <= messages[i + 1].timestamp


def test_log_scalar_metrics_with_implicit_step(ex):
    messages = {}

    @ex.main
    def main_function(_run):
        for i in range(10):
            val = i * i
            ex.log_scalar("training.loss", val)
            ex.log_scalar("training.accuracy", val + 1)
        messages["messages"] = ex.current_run._metrics.get_last_metrics()

    ex.run()
    assert ex.current_run is not None
    messages = messages["messages"]
    tr_loss_messages = messages[0].entries
    tr_acc_messages = messages[1].entries

    assert len(tr_loss_messages) == 10
    # both should have 10 records
    assert len(tr_acc_messages) == len(tr_loss_messages)
    for i in range(len(tr_loss_messages) - 1):
        assert tr_loss_messages[i].step < tr_loss_messages[i + 1].step
        assert tr_loss_messages[i].step == i
        assert tr_loss_messages[i].timestamp <= tr_loss_messages[i + 1].timestamp

        assert tr_acc_messages[i].step < tr_acc_messages[i + 1].step
        assert tr_acc_messages[i].step == i
        assert tr_acc_messages[i].timestamp <= tr_acc_messages[i + 1].timestamp


@pytest.mark.skipif(not opt.has_numpy, reason="requires numpy")
def test_log_scalar_metric_numpy():
    import numpy as np

    mlogger = MetricsLogger()
    mlogger.log_scalar_metric("test.numpy", np.int32(1), 1)
    entry = mlogger.metrics["test.numpy"].entries.get_nowait()
    # Use `is` to check type and value as `np.int32(1) == 1` will return True.
    assert entry.value is 1


@pytest.mark.skipif(not opt.has_pint, reason="requires pint")
def test_log_scalar_metric_pint():
    import pint

    mlogger = MetricsLogger()
    mlogger.log_scalar_metric("test.pint", pint.Quantity(1, "meter"), 1)
    entry = mlogger.metrics["test.pint"].entries.get_nowait()
    assert entry.value == 1
    assert mlogger.metrics["test.pint"].meta["units"] == "meter"


@pytest.mark.skipif(not opt.has_pint, reason="requires pint")
def test_log_scalar_metric_pint_bad_units():
    import pint

    mlogger = MetricsLogger()
    mlogger.log_scalar_metric("test.pint", pint.Quantity(1, "meter"), 1)
    with pytest.raises(pint.DimensionalityError):
        mlogger.log_scalar_metric("test.pint", pint.Quantity(1, "hertz"), 2)


def test_linearize_metrics():
    entries = [
        MetricLogEntry(
            "training.loss",
            {},
            [
                ScalarMetricLogEntry(10, datetime.datetime.utcnow(), 100),
                ScalarMetricLogEntry(20, datetime.datetime.utcnow(), 200),
            ],
        ),
        MetricLogEntry(
            "training.accuracy",
            {},
            [
                ScalarMetricLogEntry(5, datetime.datetime.utcnow(), 50),
                ScalarMetricLogEntry(10, datetime.datetime.utcnow(), 100),
                ScalarMetricLogEntry(15, datetime.datetime.utcnow(), 150),
                ScalarMetricLogEntry(30, datetime.datetime.utcnow(), 300),
            ],
        ),
    ]
    linearized = linearize_metrics(entries)
    assert type(linearized) == dict
    assert len(linearized.keys()) == len(entries)
    for entry in entries:
        assert entry.name in linearized
        assert len(linearized[entry.name]["steps"]) == len(entry.entries)
        assert len(linearized[entry.name]["values"]) == len(entry.entries)
        assert len(linearized[entry.name]["timestamps"]) == len(entry.entries)
    assert linearized["training.accuracy"]["steps"] == [5, 10, 15, 30]
    assert linearized["training.accuracy"]["values"] == [50, 100, 150, 300]
    assert linearized["training.loss"]["steps"] == [10, 20]
    assert linearized["training.loss"]["values"] == [100, 200]
