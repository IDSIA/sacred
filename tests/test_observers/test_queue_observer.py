from collections import OrderedDict

from sacred.observers.queue import QueueObserver
import mock
import pytest


@pytest.fixture
def queue_observer():
    return QueueObserver(
        mock.MagicMock(),
        interval=0.01,
        retry_interval=0.01,
    )


def test_started_event(queue_observer):
    queue_observer.started_event("args", kwds="kwargs")
    assert queue_observer._worker.is_alive()
    queue_observer.join()
    assert queue_observer._covered_observer.method_calls[0][0] == "started_event"
    assert queue_observer._covered_observer.method_calls[0][1] == ("args",)
    assert queue_observer._covered_observer.method_calls[0][2] == {"kwds": "kwargs"}


@pytest.mark.parametrize(
    "event_name",
    ["heartbeat_event", "resource_event", "artifact_event"],
)
def test_non_terminal_generic_events(queue_observer, event_name):
    queue_observer.started_event()
    getattr(queue_observer, event_name)("args", kwds="kwargs")
    queue_observer.join()
    assert queue_observer._covered_observer.method_calls[1][0] == event_name
    assert queue_observer._covered_observer.method_calls[1][1] == ("args",)
    assert queue_observer._covered_observer.method_calls[1][2] == {"kwds": "kwargs"}


@pytest.mark.parametrize(
    "event_name",
    ["completed_event", "interrupted_event", "failed_event"],
)
def test_terminal_generic_events(queue_observer, event_name):
    queue_observer.started_event()
    getattr(queue_observer, event_name)("args", kwds="kwargs")
    assert queue_observer._covered_observer.method_calls[1][0] == event_name
    assert queue_observer._covered_observer.method_calls[1][1] == ("args",)
    assert queue_observer._covered_observer.method_calls[1][2] == {"kwds": "kwargs"}
    assert not queue_observer._worker.is_alive()


def test_log_metrics(queue_observer):
    queue_observer.started_event()
    first = ("a", [1])
    second = ("b", [2])
    queue_observer.log_metrics(OrderedDict([first, second]), "info")
    queue_observer.join()
    assert queue_observer._covered_observer.method_calls[1][0] == "log_metrics"
    assert queue_observer._covered_observer.method_calls[1][1] == (first[0], first[1], "info")
    assert queue_observer._covered_observer.method_calls[1][2] == {}
    assert queue_observer._covered_observer.method_calls[2][0] == "log_metrics"
    assert queue_observer._covered_observer.method_calls[2][1] == (second[0], second[1], "info")
    assert queue_observer._covered_observer.method_calls[2][2] == {}
