#!/usr/bin/env python
# coding=utf-8

__all__ = ("RunObserver", "td_format")


class RunObserver:
    """Defines the interface for all run observers."""

    priority = 0

    def queued_event(
        self, ex_info, command, host_info, queue_time, config, meta_info, _id
    ):
        pass

    def started_event(
        self, ex_info, command, host_info, start_time, config, meta_info, _id
    ):
        pass

    def heartbeat_event(self, info, captured_out, beat_time, result):
        pass

    def completed_event(self, stop_time, result):
        pass

    def interrupted_event(self, interrupt_time, status):
        pass

    def failed_event(self, fail_time, fail_trace):
        pass

    def resource_event(self, filename):
        pass

    def artifact_event(self, name, filename, metadata=None, content_type=None):
        pass

    def log_metrics(self, metrics_by_name, info):
        pass

    def join(self):
        pass


# http://stackoverflow.com/questions/538666/python-format-timedelta-to-string
def td_format(td_object):
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
