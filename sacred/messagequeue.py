#!/usr/bin/env python
# coding=utf-8
import sys

if sys.version_info[0] == 2:
    from Queue import Queue
else:
    from queue import Queue, Empty


class SacredMQ:

    def __init__(self):
        self.consumers = []

    def add_consumer(self):
        consumer = Consumer()
        self.consumers.append(consumer)
        return consumer

    def publish(self, message):
        for consumer in self.consumers:
            consumer.add_message(message)


class Consumer:
    def __init__(self):
        self.queue = Queue()

    def add_message(self, message):
        self.queue.put(message)

    def has_message(self):
        return not self.queue.empty()

    def read_all(self):
        read_up_to = self.queue.qsize()
        messages = []
        for i in range(read_up_to):
            try:
                messages.append(self.queue.get_nowait())
            except Empty:
                pass
        return messages
