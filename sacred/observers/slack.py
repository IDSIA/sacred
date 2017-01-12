#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from sacred.observers.base import RunObserver
from sacred.config.config_files import load_config_file
import requests
import json


# http://stackoverflow.com/questions/538666/python-format-timedelta-to-string
def td_format(td_object):
    seconds = int(td_object.total_seconds())
    periods = [
        ('year', 60 * 60 * 24 * 365),
        ('month', 60 * 60 * 24 * 30),
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1)
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


class SlackObserver(RunObserver):
    @classmethod
    def from_config(cls, filename):
        d = load_config_file(filename)
        return cls(**d)

    def __init__(self, webhook_url, bot_name="sacred-bot", icon=":angel:"):
        self.webhook_url = webhook_url
        self.bot_name = bot_name
        self.icon = icon
        self.completed_text = ":white_check_mark: *{ex_info[name]}* ({_id}) completed after {elapsed_time} with result={result}"
        self.interrupted_text = ":warning: *{ex_info[name]}* ({_id}) interrupted after {elapsed_time}"
        self.failed_text = ":x: *{ex_info[name]}* ({_id}) failed with `{error}`"
        self.run = None

    def started_event(self, ex_info, command, host_info, start_time, config,
                      meta_info, _id):
        self.run = {
            '_id': _id,
            'config': config,
            'start_time': start_time,
            'ex_info': ex_info,
            'command': command,
            'host_info': host_info,
        }

    def completed_event(self, stop_time, result):
        if self.completed_text is None:
            return

        self.run['result'] = result
        self.run['stop_time'] = stop_time
        self.run['elapsed_time'] = td_format(stop_time - self.run['start_time'])

        data = {
            "username": self.bot_name,
            "icon_emoji": self.icon,
            "text": self.completed_text.format(**self.run)
        }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        requests.post(self.webhook_url, data=json.dumps(data), headers=headers)

    def interrupted_event(self, interrupt_time, status):
        if self.interrupted_text is None:
            return

        self.run['status'] = status
        self.run['interrupt_time'] = interrupt_time
        self.run['elapsed_time'] = td_format(interrupt_time - self.run['start_time'])

        data = {
            "username": self.bot_name,
            "icon_emoji": self.icon,
            "text": self.interrupted_text.format(**self.run)
        }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        requests.post(self.webhook_url, data=json.dumps(data), headers=headers)

    def failed_event(self, fail_time, fail_trace):
        if self.failed_text is None:
            return

        self.run['fail_trace'] = fail_trace
        self.run['error'] = fail_trace[-1].strip()
        self.run['fail_time'] = fail_time
        self.run['elapsed_time'] = td_format(fail_time - self.run['start_time'])

        data = {
            "username": self.bot_name,
            "icon_emoji": self.icon,
            "text": self.completed_text
        }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        requests.post(self.webhook_url, data=json.dumps(data), headers=headers)