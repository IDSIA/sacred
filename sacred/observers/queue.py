# coding=utf-8
from __future__ import division, print_function, unicode_literals
from collections import namedtuple
from queue import Queue
from sacred.observers.base import RunObserver
from sacred.utils import IntervalTimer

WrappedEvent = namedtuple("WrappedEvent", "name args kwargs")


class QueueObserver(RunObserver):

    def __init__(self, covered_observer, interval=20):
        self.covered_observer = covered_observer
        self._queue = Queue()
        self._stop_worker_event, self._worker = IntervalTimer.create(
            self._run,
            interval=interval,
        )
        self._worker.start()

    def queued_event(self, *args, **kwargs):
        self._queue.put(WrappedEvent("queued_event", args, kwargs))

    def started_event(self, *args, **kwargs):
        # Putting the started event on the queue makes no sense
        # as it is required for initialization of the covered observer.
        return self.covered_observer.started_event(*args, **kwargs)

    def heartbeat_event(self, *args, **kwargs):
        self._queue.put(WrappedEvent("heartbeat_event", args, kwargs))

    def completed_event(self, *args, **kwargs):
        self._queue.put(WrappedEvent("completed_event", args, kwargs))
        self.join()

    def interrupted_event(self, *args, **kwargs):
        self._queue.put(WrappedEvent("interrupted_event", args, kwargs))
        self.join()

    def failed_event(self, *args, **kwargs):
        self._queue.put(WrappedEvent("failed_event", args, kwargs))
        self.join()

    def resource_event(self, *args, **kwargs):
        self._queue.put(WrappedEvent("resource_event", args, kwargs))

    def artifact_event(self, *args, **kwargs):
        self._queue.put(WrappedEvent("artifact_event", args, kwargs))

    def _run(self):
        while not self._queue.empty():
            try:
                event = self._queue.get()
            except IndexError:
                # Currently there is no event on the queue so
                # just go back to sleep.
                pass
            else:
                try:
                    method = getattr(self.covered_observer, event.name)
                except NameError as e:
                    # covered observer does not implement event handler
                    # for the event, so just
                    # discard the message.
                    print(e)
                    self._queue.task_done()
                else:
                    while True:
                        try:
                            method(*event.args, **event.kwargs)
                        except Exception as e:
                            # Something went wrong during the processing of
                            # the event so wait for some time and
                            # then try again.
                            self._stop_worker_event.wait(10)
                            print(e)
                            continue
                        else:
                            self._queue.task_done()
                            break

    def join(self):
        self._queue.join()
        self._stop_worker_event.set()
        self._worker.join(timeout=10)

    def __getattr__(self, item):
        return getattr(self.covered_observer, item)

    def __eq__(self, other):
        return self.covered_observer == other
