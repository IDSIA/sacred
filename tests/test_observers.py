#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from datetime import datetime
from sacred.observers.base import RunObserver


def test_run_observer():
    # basically to silence coverage
    r = RunObserver()
    assert r.started_event({}, 'run', {}, datetime.now(), {}, 'comment') is None
    assert r.heartbeat_event({}, '', datetime.now()) is None
    assert r.completed_event(datetime.now(), 123) is None
    assert r.interrupted_event(datetime.now(), "INTERRUPTED") is None
    assert r.failed_event(datetime.now(), 'trace') is None
    assert r.artifact_event('foo.txt') is None
    assert r.resource_event('foo.txt') is None
