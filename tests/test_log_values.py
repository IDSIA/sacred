import pytest
from sacred import Experiment, messagequeue


@pytest.fixture()
def ex():
    return Experiment("Test experiment")


def test_log_value(ex):
    test_log_value.metrics_consumer = None #type: messagequeue.Consumer
    @ex.main
    def main_function(_run):
        test_log_value.metrics_consumer = _run.metrics.register_listener()
        for i in range(10, 100, 5):
            val = i*i
            _run.metrics.log_scalar_metric("training.loss", i, val)

    ex.run()
    assert ex.current_run is not None
    assert test_log_value.metrics_consumer is not None
    assert test_log_value.metrics_consumer.has_message()
    messages = test_log_value.metrics_consumer.read_all()
    assert len(messages) == (100 - 10)/5
    for i in range(len(messages)-1):
        assert messages[i]["timestep"] < messages[i+1]["timestep"]
        assert messages[i]["timestamp"] <= messages[i + 1]["timestamp"]
