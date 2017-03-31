import datetime

import pytest
from sacred import Experiment, messagequeue
from sacred.metrics_logger import ScalarMetricLogEntry, linearize_metrics


@pytest.fixture()
def ex():
    return Experiment("Test experiment")


def test_log_scalar_metric(ex):
    test_log_scalar_metric.metrics_consumer = None #type: messagequeue.Consumer
    @ex.main
    def main_function(_run):
        test_log_scalar_metric.metrics_consumer = _run.metrics.register_listener()
        for i in range(10, 100, 5):
            val = i*i
            _run.metrics.log_scalar_metric("training.loss", i, val)

    ex.run()
    assert ex.current_run is not None
    assert test_log_scalar_metric.metrics_consumer is not None
    assert test_log_scalar_metric.metrics_consumer.has_message()
    messages = test_log_scalar_metric.metrics_consumer.read_all()
    assert len(messages) == (100 - 10)/5
    for i in range(len(messages)-1):
        assert messages[i].step < messages[i+1].step
        assert messages[i].timestamp <= messages[i + 1].timestamp


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
    assert len(linearized["training.loss"]["x"]) == 2
    assert len(linearized["training.loss"]["y"]) == 2
    assert len(linearized["training.loss"]["timestamps"]) == 2
    assert len(linearized["training.accuracy"]["x"]) == 4
    assert len(linearized["training.accuracy"]["y"]) == 4
    assert len(linearized["training.accuracy"]["timestamps"]) == 4
    assert linearized["training.accuracy"]["x"] == [5, 10, 15, 30]
    assert linearized["training.accuracy"]["y"] == [50, 100, 150, 300]
    assert linearized["training.loss"]["x"] == [10, 20]
    assert linearized["training.loss"]["y"] == [100, 200]
