#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from sacred.observers.base import RunObserver
from sacred.config.config_files import load_config_file
from sacred.optional import telegram  # type: telegram
import logging


# http://stackoverflow.com/questions/538666/python-format-timedelta-to-string
def td_format(td_object):
    seconds = int(td_object.total_seconds())
    if seconds == 0:
        return "less than a second"

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


class TelegramObserver(RunObserver):
    """Sends a message to Telegram upon completion/failing of an experiment."""

    @classmethod
    def from_config(cls, filename):
        """
        Create a TelegramObserver from a given configuration file.

        The file can be in any format supported by Sacred
        (.json, .pickle, [.yaml]).
        It has to specify a ``token`` and a ``chat_id`` and can optionally set
        ``silent_completion``,``completed_text``, ``interrupted_text``, and
        ``failed_text``.
        """
        d = load_config_file(filename)
        obs = None
        if 'token' in d and 'chat_id' in d:
            bot = telegram.Bot(d['token'])
            obs = cls(bot, **d)
        else:
            raise ValueError("Telegram configuration file must contain "
                             "entries for 'token' and 'chat_id'!")
        for k in ['completed_text', 'interrupted_text', 'failed_text']:
            if k in d:
                setattr(obs, k, d[k])
        return obs

    def __init__(self, bot, chat_id, silent_completion=False, **kwargs):
        self.silent_completion = silent_completion
        self.chat_id = chat_id
        self.bot = bot

        self.started_text = "♻ *{experiment[name]}* " \
                            "started at _{start_time}_ " \
                            "on host `{host_info[hostname]}`"
        self.completed_text = "✅ *{experiment[name]}* " \
                              "completed after _{elapsed_time}_ " \
                              "with result=`{result}`"
        self.interrupted_text = "⚠ *{experiment[name]}* " \
                                "interrupted after _{elapsed_time}_"
        self.failed_text = "❌ *{experiment[name]}* failed after " \
                           "_{elapsed_time}_ with `{error}`\n\n" \
                           "Backtrace:\n```{backtrace}```"
        self.run = None

    def started_event(self, ex_info, command, host_info, start_time, config,
                      meta_info, _id):
        self.run = {
            '_id': _id,
            'config': config,
            'start_time': start_time,
            'experiment': ex_info,
            'command': command,
            'host_info': host_info,
        }
        try:
            self.bot.send_message(chat_id=self.chat_id,
                                  text=self.get_started_text(),
                                  disable_notification=True,
                                  parse_mode=telegram.ParseMode.MARKDOWN)
        except Exception as e:
            log = logging.getLogger('telegram-observer')
            log.warning('failed to send start_event message via telegram.',
                        exc_info=e)

    def get_started_text(self):
        return self.started_text.format(**self.run)

    def get_completed_text(self):
        return self.completed_text.format(**self.run)

    def get_interrupted_text(self):
        return self.interrupted_text.format(**self.run)

    def get_failed_text(self):
        return self.failed_text.format(
            backtrace=''.join(self.run['fail_trace']), **self.run)

    def completed_event(self, stop_time, result):
        if self.completed_text is None:
            return

        self.run['result'] = result
        self.run['stop_time'] = stop_time
        self.run['elapsed_time'] = td_format(stop_time -
                                             self.run['start_time'])

        try:
            self.bot.send_message(chat_id=self.chat_id,
                                  text=self.get_completed_text(),
                                  disable_notification=self.silent_completion,
                                  parse_mode=telegram.ParseMode.MARKDOWN)
        except Exception as e:
            log = logging.getLogger('telegram-observer')
            log.warning('failed to send completed_event message via telegram.',
                        exc_info=e)

    def interrupted_event(self, interrupt_time, status):
        if self.interrupted_text is None:
            return

        self.run['status'] = status
        self.run['interrupt_time'] = interrupt_time
        self.run['elapsed_time'] = td_format(interrupt_time -
                                             self.run['start_time'])

        try:
            self.bot.send_message(chat_id=self.chat_id,
                                  text=self.get_interrupted_text(),
                                  disable_notification=False,
                                  parse_mode=telegram.ParseMode.MARKDOWN)
        except Exception as e:
            log = logging.getLogger('telegram-observer')
            log.warning('failed to send interrupted_event message '
                        'via telegram.', exc_info=e)

    def failed_event(self, fail_time, fail_trace):
        if self.failed_text is None:
            return

        self.run['fail_trace'] = fail_trace
        self.run['error'] = fail_trace[-1].strip()
        self.run['fail_time'] = fail_time
        self.run['elapsed_time'] = td_format(fail_time -
                                             self.run['start_time'])

        try:
            self.bot.send_message(chat_id=self.chat_id,
                                  text=self.get_failed_text(),
                                  disable_notification=False,
                                  parse_mode=telegram.ParseMode.MARKDOWN)
        except Exception as e:
            log = logging.getLogger('telegram-observer')
            log.warning('failed to send failed_event message via telegram.',
                        exc_info=e)
