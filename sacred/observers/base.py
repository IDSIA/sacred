#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

__sacred__ = True  # marks files that should be filtered from stack traces

__all__ = ('RunObserver',)


class RunObserver(object):
    """Defines the interface for all run observers."""

    priority = 0

    def queued_event(self, ex_info, command, queue_time, config, meta_info,
                     _id):
        pass

    def started_event(self, ex_info, command, host_info, start_time, config,
                      meta_info, _id):
        pass

    def heartbeat_event(self, info, captured_out, beat_time):
        pass

    def completed_event(self, stop_time, result):
        pass

    def interrupted_event(self, interrupt_time, status):
        pass

    def failed_event(self, fail_time, fail_trace):
        pass

    def resource_event(self, filename):
        pass

    def artifact_event(self, name, filename):
        pass
