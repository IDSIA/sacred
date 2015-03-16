#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

__sacred__ = True  # marks files that should be filtered from stack traces

__all__ = ('RunObserver', 'DebugObserver')


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


class DebugObserver(RunObserver):
    def started_event(self, ex_info, host_info, start_time, config):
        print('experiment_started_event')

    def heartbeat_event(self, info, captured_out, beat_time):
        print('experiment_info_updated')

    def completed_event(self, stop_time, result):
        print('experiment_completed_event')

    def interrupted_event(self, interrupt_time):
        print('experiment_interrupted_event')

    def failed_event(self, fail_time, fail_trace):
        print('experiment_failed_event')

    def resource_event(self, filename):
        print('resource_event: {}'.format(filename))

    def artifact_event(self, filename):
        print('artifact_event: {}'.format(filename))
