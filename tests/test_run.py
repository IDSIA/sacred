#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from datetime import datetime
import mock
import os
import pytest
import tempfile
import sys

from sacred.run import Run
from sacred.config.config_summary import ConfigSummary
from sacred.utils import (ObserverError, SacredInterrupt, TimeoutInterrupt,
                          apply_backspaces_and_linefeeds)


@pytest.fixture
def run():
    config = {'a': 17, 'foo': {'bar': True, 'baz': False}, 'seed': 1234}
    config_mod = ConfigSummary()
    signature = mock.Mock()
    signature.name = 'main_func'
    main_func = mock.Mock(return_value=123, prefix='', signature=signature)
    logger = mock.Mock()
    observer = [mock.Mock(priority=10)]
    return Run(config, config_mod, main_func, observer, logger, logger, {},
               {}, [], [])


def test_run_attributes(run):
    assert isinstance(run.config, dict)
    assert isinstance(run.config_modifications, ConfigSummary)
    assert isinstance(run.experiment_info, dict)
    assert isinstance(run.host_info, dict)
    assert isinstance(run.info, dict)


def test_run_state_attributes(run):
    assert run.start_time is None
    assert run.stop_time is None
    assert run.captured_out is None
    assert run.result is None


def test_run_run(run):
    assert run() == 123
    assert (run.start_time - datetime.utcnow()).total_seconds() < 1
    assert (run.stop_time - datetime.utcnow()).total_seconds() < 1
    assert run.result == 123
    assert run.captured_out == ''


def test_run_emits_events_if_successful(run):
    run()

    observer = run.observers[0]
    assert observer.started_event.called
    assert observer.heartbeat_event.called
    assert observer.completed_event.called
    assert not observer.interrupted_event.called
    assert not observer.failed_event.called


@pytest.mark.parametrize('exception,status', [
    (KeyboardInterrupt, 'INTERRUPTED'),
    (SacredInterrupt, 'INTERRUPTED'),
    (TimeoutInterrupt, 'TIMEOUT'),
])
def test_run_emits_events_if_interrupted(run, exception, status):
    observer = run.observers[0]
    run.main_function.side_effect = exception
    with pytest.raises(exception):
        run()
    assert observer.started_event.called
    assert observer.heartbeat_event.called
    assert not observer.completed_event.called
    assert observer.interrupted_event.called
    observer.interrupted_event.assert_called_with(
        interrupt_time=run.stop_time,
        status=status)
    assert not observer.failed_event.called


def test_run_emits_events_if_failed(run):
    observer = run.observers[0]
    run.main_function.side_effect = TypeError
    with pytest.raises(TypeError):
        run()
    assert observer.started_event.called
    assert observer.heartbeat_event.called
    assert not observer.completed_event.called
    assert not observer.interrupted_event.called
    assert observer.failed_event.called


def test_run_started_event(run):
    observer = run.observers[0]
    run()
    observer.started_event.assert_called_with(
        command='main_func',
        ex_info=run.experiment_info,
        host_info=run.host_info,
        start_time=run.start_time,
        config=run.config,
        meta_info={},
        _id=None
    )


def test_run_completed_event(run):
    observer = run.observers[0]
    run()
    observer.completed_event.assert_called_with(
        stop_time=run.stop_time,
        result=run.result
    )


def test_run_heartbeat_event(run):
    observer = run.observers[0]
    run.info['test'] = 321
    run()
    call_args, call_kwargs = observer.heartbeat_event.call_args_list[0]
    assert call_kwargs['info'] == run.info
    assert call_kwargs['captured_out'] == ""
    assert (call_kwargs['beat_time'] - datetime.utcnow()).total_seconds() < 1


def test_run_artifact_event(run):
    observer = run.observers[0]
    handle, f_name = tempfile.mkstemp()
    run.add_artifact(f_name, name='foobar')
    observer.artifact_event.assert_called_with(filename=f_name, name='foobar')
    os.close(handle)
    os.remove(f_name)


def test_run_resource_event(run):
    observer = run.observers[0]
    handle, f_name = tempfile.mkstemp()
    run.open_resource(f_name)
    observer.resource_event.assert_called_with(filename=f_name)
    os.close(handle)
    os.remove(f_name)


def test_run_cannot_be_started_twice(run):
    run()
    with pytest.raises(RuntimeError):
        run()


def test_run_observer_failure_on_startup_not_caught(run):
    observer = run.observers[0]
    observer.started_event.side_effect = ObserverError
    with pytest.raises(ObserverError):
        run()


def test_run_observer_error_in_heartbeat_is_caught(run):
    observer = run.observers[0]
    observer.heartbeat_event.side_effect = ObserverError
    run()
    assert observer in run._failed_observers
    assert observer.started_event.called
    assert observer.heartbeat_event.called
    assert observer.completed_event.called


def test_run_exception_in_heartbeat_is_not_caught(run):
    observer = run.observers[0]
    observer.heartbeat_event.side_effect = TypeError
    with pytest.raises(TypeError):
        run()
    assert observer in run._failed_observers
    assert observer.started_event.called
    assert observer.heartbeat_event.called
    assert not observer.completed_event.called
    assert not observer.interrupted_event.called
    # assert observer.failed_event.called  # TODO: make this happen


def test_run_exception_in_completed_event_is_caught(run):
    observer = run.observers[0]
    observer2 = mock.Mock(priority=20)
    run.observers.append(observer2)
    observer.completed_event.side_effect = TypeError
    run()
    assert observer.completed_event.called
    assert observer2.completed_event.called


def test_run_exception_in_interrupted_event_is_caught(run):
    observer = run.observers[0]
    observer2 = mock.Mock(priority=20)
    run.observers.append(observer2)
    observer.interrupted_event.side_effect = TypeError
    run.main_function.side_effect = KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        run()
    assert observer.interrupted_event.called
    assert observer2.interrupted_event.called


def test_run_exception_in_failed_event_is_caught(run):
    observer = run.observers[0]
    observer2 = mock.Mock(priority=20)
    run.observers.append(observer2)
    observer.failed_event.side_effect = TypeError
    run.main_function.side_effect = AttributeError
    with pytest.raises(AttributeError):
        run()
    assert observer.failed_event.called
    assert observer2.failed_event.called


def test_unobserved_run_doesnt_emit(run):
    observer = run.observers[0]
    run.unobserved = True
    run()
    assert not observer.started_event.called
    assert not observer.heartbeat_event.called
    assert not observer.completed_event.called
    assert not observer.interrupted_event.called
    assert not observer.failed_event.called


def test_captured_out_filter(run, capsys):
    def print_mock_progress():
        sys.stdout.write('progress 0')
        sys.stdout.flush()
        for i in range(10):
            sys.stdout.write('\b')
            sys.stdout.write(str(i))
            sys.stdout.flush()

    run.captured_out_filter = apply_backspaces_and_linefeeds
    run.main_function.side_effect = print_mock_progress
    with capsys.disabled():
        run()
        assert run.captured_out == 'progress 9'
