import datetime

import pytest
from sacred import Experiment, messagequeue
from sacred.metrics_logger import ScalarMetricLogEntry, linearize_metrics


@pytest.fixture()
def ex():
    return Experiment("Test experiment")


def test_log_scalar_metric_with_run(ex):
    test_log_scalar_metric_with_run.metrics_consumer = None #type: messagequeue.Consumer
    START = 10
    END = 100
    STEP_SIZE = 5
    @ex.main
    def main_function(_run):
        test_log_scalar_metric_with_run.metrics_consumer = _run._metrics.register_listener()
        for i in range(START, END, STEP_SIZE):
            val = i*i
            _run.log_scalar("training.loss", val, i)

    ex.run()
    assert ex.current_run is not None
    assert test_log_scalar_metric_with_run.metrics_consumer is not None
    assert test_log_scalar_metric_with_run.metrics_consumer.has_message()
    messages = test_log_scalar_metric_with_run.metrics_consumer.read_all()
    assert len(messages) == (END - START)/STEP_SIZE
    for i in range(len(messages)-1):
        assert messages[i].step < messages[i+1].step
        assert messages[i].step == START + i * STEP_SIZE
        assert messages[i].timestamp <= messages[i + 1].timestamp


def test_log_scalar_metric_with_ex(ex):
    test_log_scalar_metric_with_ex.metrics_consumer = None #type: messagequeue.Consumer
    START = 10
    END = 100
    STEP_SIZE = 5
    @ex.main
    def main_function(_run):
        test_log_scalar_metric_with_ex.metrics_consumer = _run._metrics.register_listener()
        for i in range(START, END, STEP_SIZE):
            val = i*i
            ex.log_scalar("training.loss", val, i)
    ex.run()
    assert ex.current_run is not None
    assert test_log_scalar_metric_with_ex.metrics_consumer is not None
    assert test_log_scalar_metric_with_ex.metrics_consumer.has_message()
    messages = test_log_scalar_metric_with_ex.metrics_consumer.read_all()
    assert len(messages) == (END - START) / STEP_SIZE
    for i in range(len(messages)-1):
        assert messages[i].step < messages[i+1].step
        assert messages[i].step == START + i * STEP_SIZE
        assert messages[i].timestamp <= messages[i + 1].timestamp


def test_log_scalar_metric_with_implicit_step(ex):
    test_log_scalar_metric_with_implicit_step.metrics_consumer = None #type: messagequeue.Consumer

    @ex.main
    def main_function(_run):
        test_log_scalar_metric_with_implicit_step.metrics_consumer = _run._metrics.register_listener()
        for i in range(10):
            val = i*i
            ex.log_scalar("training.loss", val)
    ex.run()
    assert ex.current_run is not None
    assert test_log_scalar_metric_with_implicit_step.metrics_consumer is not None
    assert test_log_scalar_metric_with_implicit_step.metrics_consumer.has_message()
    messages = test_log_scalar_metric_with_implicit_step.metrics_consumer.read_all()
    assert len(messages) == 10
    for i in range(len(messages)-1):
        assert messages[i].step < messages[i+1].step
        assert messages[i].step == i
        assert messages[i].timestamp <= messages[i + 1].timestamp


def test_log_scalar_metrics_with_implicit_step(ex):
    test_log_scalar_metrics_with_implicit_step.metrics_consumer = None #type: messagequeue.Consumer

    @ex.main
    def main_function(_run):
        test_log_scalar_metrics_with_implicit_step.metrics_consumer = _run._metrics.register_listener()
        for i in range(10):
            val = i*i
            ex.log_scalar("training.loss", val)
            ex.log_scalar("training.accuracy", val + 1)
    ex.run()
    assert ex.current_run is not None
    assert test_log_scalar_metrics_with_implicit_step.metrics_consumer is not None
    assert test_log_scalar_metrics_with_implicit_step.metrics_consumer.has_message()
    messages = test_log_scalar_metrics_with_implicit_step.metrics_consumer.read_all()
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
    entries = [ScalarMetricLogEntry("training.loss", 10, datetime.datetime.utcnow(), 100),
               ScalarMetricLogEntry("training.accuracy", 5, datetime.datetime.utcnow(), 50),
               ScalarMetricLogEntry("training.loss", 20, datetime.datetime.utcnow(), 200),
               ScalarMetricLogEntry("training.accuracy", 10, datetime.datetime.utcnow(), 100),
               ScalarMetricLogEntry("training.accuracy", 15, datetime.datetime.utcnow(), 150),
               ScalarMetricLogEntry("training.accuracy", 30, datetime.datetime.utcnow(), 300)]
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
