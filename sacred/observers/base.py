#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

__sacred__ = True  # marks files that should be filtered from stack traces

__all__ = ('RunObserver',)


class RunObserver(object):

    """Defines the interface for all run observers."""

    def started_event(self, ex_info, host_info, start_time, config):
        pass

    def heartbeat_event(self, info, captured_out, beat_time):
        pass

    def completed_event(self, stop_time, result):
        pass

    def interrupted_event(self, interrupt_time):
        pass

    def failed_event(self, fail_time, fail_trace):
        pass

    def resource_event(self, filename):
        pass

    def artifact_event(self, filename):
        pass
