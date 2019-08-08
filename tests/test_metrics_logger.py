#!/usr/bin/env python
# coding=utf-8

import datetime
import pytest
from sacred import Experiment
from sacred.metrics_logger import ScalarMetricLogEntry, linearize_metrics


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
    messages = messages["messages"]
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
    messages = messages["messages"]
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
    messages = messages["messages"]
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
    tr_loss_messages = [m for m in messages if m.name == "training.loss"]
    tr_acc_messages = [m for m in messages if m.name == "training.accuracy"]

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


def test_linearize_metrics():
    entries = [
        ScalarMetricLogEntry("training.loss", 10, datetime.datetime.utcnow(), 100),
        ScalarMetricLogEntry("training.accuracy", 5, datetime.datetime.utcnow(), 50),
        ScalarMetricLogEntry("training.loss", 20, datetime.datetime.utcnow(), 200),
        ScalarMetricLogEntry("training.accuracy", 10, datetime.datetime.utcnow(), 100),
        ScalarMetricLogEntry("training.accuracy", 15, datetime.datetime.utcnow(), 150),
        ScalarMetricLogEntry("training.accuracy", 30, datetime.datetime.utcnow(), 300),
    ]
    linearized = linearize_metrics(entries)
    assert type(linearized) == dict
    assert len(linearized.keys()) == 2
    assert "training.loss" in linearized
    assert "training.accuracy" in linearized
    assert len(linearized["training.loss"]["steps"]) == 2
    assert len(linearized["training.loss"]["values"]) == 2
    assert len(linearized["training.loss"]["timestamps"]) == 2
    assert len(linearized["training.accuracy"]["steps"]) == 4
    assert len(linearized["training.accuracy"]["values"]) == 4
    assert len(linearized["training.accuracy"]["timestamps"]) == 4
    assert linearized["training.accuracy"]["steps"] == [5, 10, 15, 30]
    assert linearized["training.accuracy"]["values"] == [50, 100, 150, 300]
    assert linearized["training.loss"]["steps"] == [10, 20]
    assert linearized["training.loss"]["values"] == [100, 200]
