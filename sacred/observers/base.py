#!/usr/bin/env python
# coding=utf-8
from __future__ import annotations
from typing import Any


__all__ = ("RunObserver", "td_format")


from datetime import datetime, timedelta
from sacred.config.captured_function import CapturedFunction

from sacred.config.config_dict import ConfigDict


class RunObserver:
    """Defines the interface for all run observers."""

    priority = 0

    def queued_event(
        self,
        ex_info: dict,
        command: CapturedFunction,
        host_info: dict,
        queue_time: datetime,
        config: ConfigDict,
        meta_info: dict,
        _id,
    ):
        pass

    def started_event(
        self,
        ex_info: dict,
        command: CapturedFunction,
        host_info: dict,
        start_time: datetime,
        config: ConfigDict,
        meta_info: dict,
        _id,
    ):
        pass

    def heartbeat_event(
        self, info: dict, captured_out: str, beat_time: datetime, result: Any | None
    ):
        pass

    def completed_event(self, stop_time: datetime, result: Any | None):
        pass

    def interrupted_event(self, interrupt_time: datetime, status: str):
        pass

    def failed_event(self, fail_time: datetime, fail_trace: str):
        pass

    def resource_event(self, filename: str):
        pass

    def artifact_event(
        self, name: str, filename: str, metadata: dict = None, content_type: str = None
    ):
        pass

    def log_metrics(self, metrics_by_name: dict[str, dict[str, list]], info: dict):
        pass

    def join(self):
        pass


# http://stackoverflow.com/questions/538666/python-format-timedelta-to-string
def td_format(td_object: timedelta):
    seconds = int(td_object.total_seconds())
    if seconds == 0:
        return "less than a second"

    periods = [
        ("year", 60 * 60 * 24 * 365),
        ("month", 60 * 60 * 24 * 30),
        ("day", 60 * 60 * 24),
        ("hour", 60 * 60),
        ("minute", 60),
        ("second", 1),
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            if period_value == 1:
                strings.append("%s %s" % (period_value, period_name))
            else:
                strings.append("%s %ss" % (period_value, period_name))

    return ", ".join(strings)
