from notif.notificator import SlackNotificator

import sacred

ex = sacred.Experiment("deep-address-tagger")

notificator = SlackNotificator(webhook_url="webhook_url_to_throw_notification")
# Change for a valid webhook url. Read the doc about Slack webhook for information on how to get one.

ex.add_notificator(notificator=notificator)


@ex.automain
def main():
    print("3")
    # This will also throw a message into your Slack channel.
