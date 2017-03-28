import pytest
from sacred import Experiment

@pytest.fixture()
def ex():
    return Experiment("Test experiment")


def test_log_value(ex):
    @ex.main
    def main_function(_run):
        for i in range(10, 100, 5):
            val = i*i
            _run.metrics.log_scalar_metric("training.loss", i, val)

    ex.run()
    assert ex.current_run is not None
