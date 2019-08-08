#!/usr/bin/env python
# coding=utf-8

from sacred.observers.base import RunObserver, td_format
from sacred.config.config_files import load_config_file
import logging


DEFAULT_TELEGRAM_PRIORITY = 10


class TelegramObserver(RunObserver):
    """Sends a message to Telegram upon completion/failing of an experiment."""

    @staticmethod
    def get_proxy_request(telegram_config):
        from telegram.utils.request import Request

        if telegram_config["proxy_url"].startswith("socks5"):
            urllib3_proxy_kwargs = dict()
            for key in ["username", "password"]:
                if key in telegram_config:
                    urllib3_proxy_kwargs[key] = telegram_config[key]
            return Request(
                proxy_url=telegram_config["proxy_url"],
                urllib3_proxy_kwargs=urllib3_proxy_kwargs,
            )
        elif telegram_config["proxy_url"].startswith("http"):
            cred_string = ""
            if "username" in telegram_config:
                cred_string += telegram_config["username"]
            if "password" in telegram_config:
                cred_string += ":" + telegram_config["password"]
            if len(cred_string) > 0:
                domain = telegram_config["proxy_url"].split("/")[-1].split("@")[-1]
                cred_string += "@"
                proxy_url = "http://{}{}".format(cred_string, domain)
                return Request(proxy_url=proxy_url)
            else:
                return Request(proxy_url=telegram_config["proxy_url"])
        else:
            raise Exception(
                "Proxy URL should be in format "
                "PROTOCOL://PROXY_HOST[:PROXY_PORT].\n"
                "HTTP and Socks5 are supported."
            )

    @classmethod
    def from_config(cls, filename):
        """
        Create a TelegramObserver from a given configuration file.

        The file can be in any format supported by Sacred
        (.json, .pickle, [.yaml]).
        It has to specify a ``token`` and a ``chat_id`` and can optionally set
        ``silent_completion``, ``started_text``, ``completed_text``,
        ``interrupted_text``, and ``failed_text``.
        """
        import telegram

        d = load_config_file(filename)
        request = cls.get_proxy_request(d) if "proxy_url" in d else None

        if "token" in d and "chat_id" in d:
            bot = telegram.Bot(d["token"], request=request)
            obs = cls(bot, **d)
        else:
            raise ValueError(
                "Telegram configuration file must contain "
                "entries for 'token' and 'chat_id'!"
            )
        for k in ["started_text", "completed_text", "interrupted_text", "failed_text"]:
            if k in d:
                setattr(obs, k, d[k])
        return obs

    def __init__(
        self,
        bot,
        chat_id,
        silent_completion=False,
        priority=DEFAULT_TELEGRAM_PRIORITY,
        **kwargs,
    ):
        self.silent_completion = silent_completion
        self.chat_id = chat_id
        self.bot = bot

        self.started_text = (
            "♻ *{experiment[name]}* "
            "started at _{start_time}_ "
            "on host `{host_info[hostname]}`"
        )
        self.completed_text = (
            "✅ *{experiment[name]}* "
            "completed after _{elapsed_time}_ "
            "with result=`{result}`"
        )
        self.interrupted_text = (
            "⚠ *{experiment[name]}* " "interrupted after _{elapsed_time}_"
        )
        self.failed_text = (
            "❌ *{experiment[name]}* failed after "
            "_{elapsed_time}_ with `{error}`\n\n"
            "Backtrace:\n```{backtrace}```"
        )
        self.run = None
        self.priority = priority

    def started_event(
        self, ex_info, command, host_info, start_time, config, meta_info, _id
    ):
        import telegram

        self.run = {
            "_id": _id,
            "config": config,
            "start_time": start_time,
            "experiment": ex_info,
            "command": command,
            "host_info": host_info,
        }
        if self.started_text is None:
            return
        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=self.get_started_text(),
                disable_notification=True,
                parse_mode=telegram.ParseMode.MARKDOWN,
            )
        except Exception as e:
            log = logging.getLogger("telegram-observer")
            log.warning("failed to send start_event message via telegram.", exc_info=e)

    def get_started_text(self):
        return self.started_text.format(**self.run)

    def get_completed_text(self):
        return self.completed_text.format(**self.run)

    def get_interrupted_text(self):
        return self.interrupted_text.format(**self.run)

    def get_failed_text(self):
        return self.failed_text.format(
            backtrace="".join(self.run["fail_trace"]), **self.run
        )

    def completed_event(self, stop_time, result):
        import telegram

        if self.completed_text is None:
            return

        self.run["result"] = result
        self.run["stop_time"] = stop_time
        self.run["elapsed_time"] = td_format(stop_time - self.run["start_time"])

        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=self.get_completed_text(),
                disable_notification=self.silent_completion,
                parse_mode=telegram.ParseMode.MARKDOWN,
            )
        except Exception as e:
            log = logging.getLogger("telegram-observer")
            log.warning(
                "failed to send completed_event message via telegram.", exc_info=e
            )

    def interrupted_event(self, interrupt_time, status):
        import telegram

        if self.interrupted_text is None:
            return

        self.run["status"] = status
        self.run["interrupt_time"] = interrupt_time
        self.run["elapsed_time"] = td_format(interrupt_time - self.run["start_time"])

        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=self.get_interrupted_text(),
                disable_notification=False,
                parse_mode=telegram.ParseMode.MARKDOWN,
            )
        except Exception as e:
            log = logging.getLogger("telegram-observer")
            log.warning(
                "failed to send interrupted_event message " "via telegram.", exc_info=e
            )

    def failed_event(self, fail_time, fail_trace):
        import telegram

        if self.failed_text is None:
            return

        self.run["fail_trace"] = fail_trace
        self.run["error"] = fail_trace[-1].strip()
        self.run["fail_time"] = fail_time
        self.run["elapsed_time"] = td_format(fail_time - self.run["start_time"])

        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=self.get_failed_text(),
                disable_notification=False,
                parse_mode=telegram.ParseMode.MARKDOWN,
            )
        except Exception as e:
            log = logging.getLogger("telegram-observer")
            log.warning("failed to send failed_event message via telegram.", exc_info=e)
