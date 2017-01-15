#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from datetime import datetime
from sacred.observers.base import RunObserver


def test_run_observer():
    # basically to silence coverage
    r = RunObserver()
    assert r.started_event({}, 'run', {}, datetime.utcnow(), {}, 'comment', None) is None
    assert r.heartbeat_event({}, '', datetime.utcnow()) is None
    assert r.completed_event(datetime.utcnow(), 123) is None
    assert r.interrupted_event(datetime.utcnow(), "INTERRUPTED") is None
    assert r.failed_event(datetime.utcnow(), 'trace') is None
    assert r.artifact_event('foo', 'foo.txt') is None
    assert r.resource_event('foo.txt') is None
