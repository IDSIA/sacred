#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from sacred.observers.base import RunObserver
from sacred.config.config_files import load_config_file
import logging
import os

try:
    from PIL import Image
    import tempfile
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


DEFAULT_TELEGRAM_PRIORITY = 10


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
        It has to specify a ``token`` and a ``chat_id`` (both strings) and can
        optionally set these values:

        * ``silent_success``: bool. If True, send a "silent" message upon
          successful completion.
        * ``completed_text``: str. Format string to use upon completion.
        * ``use_reply``: bool. If True, completion, interruption and failure
          messages will be sent as replies to the
          start message.
        * ``send_image``: bool. If True, and if ``PIL.Image`` is available,
          experiment results that are deemed to be images by
          ``Image.isImageType(result)`` will be sent as images with
          the ``completed_text_image`` as a caption.
        * ``completed_text_image``: str. Format string for completion when the
          result is an image. Markdown will *not* work here!
        * ``interrupted_text``: str. Format string for interruption message.
        * ``failed_text``: str. Format string for failure message.

        """
        import telegram
        d = load_config_file(filename)
        obs = None
        if 'token' in d and 'chat_id' in d:
            bot = telegram.Bot(d['token'])
            obs = cls(bot, **d)
        else:
            raise ValueError("Telegram configuration file must contain "
                             "entries for 'token' and 'chat_id'!")
        for k in ['started_text',
                  'completed_text', 'completed_text_image',
                  'interrupted_text', 'failed_text',
                  'use_reply', 'send_image']:
            if k in d:
                setattr(obs, k, d[k])
        return obs

    def __init__(self, bot, chat_id, silent_success=False,
                 use_reply=True, send_image=True,
                 priority=DEFAULT_TELEGRAM_PRIORITY, **kwargs):
        self.silent_success = silent_success
        self.chat_id = chat_id
        self.bot = bot

        self.started_text = "♻ *{experiment[name]}* " \
                            "started at _{start_time}_ " \
                            "on host `{host_info[hostname]}`"
        self.completed_text_image = "✅ {experiment[name]} " \
                                    "completed after {elapsed_time}"
        self.completed_text = "✅ *{experiment[name]}* " \
                              "completed after _{elapsed_time}_ " \
                              "with result=`{result}`"
        self.interrupted_text = "⚠ *{experiment[name]}* " \
                                "interrupted after _{elapsed_time}_"
        self.failed_text = "❌ *{experiment[name]}* failed after " \
                           "_{elapsed_time}_ with `{error}`\n\n" \
                           "Backtrace:\n```{backtrace}```"
        self.run = None
        self.priority = priority
        self.start_message = None
        self.use_reply = use_reply
        self.send_image = send_image

    def started_event(self, ex_info, command, host_info, start_time, config,
                      meta_info, _id):
        import telegram
        self.run = {
            '_id': _id,
            'config': config,
            'start_time': start_time,
            'experiment': ex_info,
            'command': command,
            'host_info': host_info,
        }
        if self.started_text is None:
            return
        try:
            self.start_message = \
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

    def get_completed_text(self, image=False):
        if image:
            return self.completed_text_image.format(**self.run)
        return self.completed_text.format(**self.run)

    def get_interrupted_text(self):
        return self.interrupted_text.format(**self.run)

    def get_failed_text(self):
        return self.failed_text.format(
            backtrace=''.join(self.run['fail_trace']), **self.run)

    def completed_event(self, stop_time, result):
        import telegram

        if self.completed_text is None:
            return

        self.run['result'] = result
        self.run['stop_time'] = stop_time
        self.run['elapsed_time'] = td_format(stop_time -
                                             self.run['start_time'])

        if self.use_reply and self.start_message:
            reply_id = self.start_message.message_id
        else:
            reply_id = None
        try:
            if HAVE_PIL and self.send_image and Image.isImageType(result):
                fh, fn = tempfile.mkstemp(suffix='.png')
                result.save(fn)
                os.close(fh)

                with open(fn, 'rb') as f:
                    self.bot.send_photo(self.chat_id, f, timeout=5,
                                        reply_to_message_id=reply_id,
                                        caption=self.get_completed_text(True))
                os.remove(fn)
            else:
                self.bot.send_message(chat_id=self.chat_id,
                                      text=self.get_completed_text(),
                                      reply_to_message_id=reply_id,
                                      disable_notification=self.silent_success,
                                      parse_mode=telegram.ParseMode.MARKDOWN)
        except Exception as e:
            log = logging.getLogger('telegram-observer')
            log.warning('failed to send completed_event message via telegram.',
                        exc_info=e)

    def interrupted_event(self, interrupt_time, status):
        import telegram

        if self.interrupted_text is None:
            return

        self.run['status'] = status
        self.run['interrupt_time'] = interrupt_time
        self.run['elapsed_time'] = td_format(interrupt_time -
                                             self.run['start_time'])

        if self.use_reply and self.start_message:
            reply_id = self.start_message.message_id
        else:
            reply_id = None
        try:
            self.bot.send_message(chat_id=self.chat_id,
                                  text=self.get_interrupted_text(),
                                  reply_to_message_id=reply_id,
                                  disable_notification=False,
                                  parse_mode=telegram.ParseMode.MARKDOWN)
        except Exception as e:
            log = logging.getLogger('telegram-observer')
            log.warning('failed to send interrupted_event message '
                        'via telegram.', exc_info=e)

    def failed_event(self, fail_time, fail_trace):
        import telegram

        if self.failed_text is None:
            return

        self.run['fail_trace'] = fail_trace
        self.run['error'] = fail_trace[-1].strip()
        self.run['fail_time'] = fail_time
        self.run['elapsed_time'] = td_format(fail_time -
                                             self.run['start_time'])

        if self.use_reply and self.start_message:
            reply_id = self.start_message.message_id
        else:
            reply_id = None
        try:
            self.bot.send_message(chat_id=self.chat_id,
                                  text=self.get_failed_text(),
                                  reply_to_message_id=reply_id,
                                  disable_notification=False,
                                  parse_mode=telegram.ParseMode.MARKDOWN)
        except Exception as e:
            log = logging.getLogger('telegram-observer')
            log.warning('failed to send failed_event message via telegram.',
                        exc_info=e)
