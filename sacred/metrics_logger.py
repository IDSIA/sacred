#!/usr/bin/env python
# coding=utf-8
import datetime

from sacred import messagequeue as mq


class MetricsLogger:
    """MetricsLogger collects metrics measured during experiments.

    MetricsLogger is the (only) part of the Metrics API.
    An instance of the class should be created for the
    Run class, such that the log_scalar_metric method is accessible
    from running experiments using _run.metrics.log_scalar_metric.
    """

    def __init__(self):
        # Create a message queue that remembers
        # calls of the log_scalar_metric
        self.mq = mq.SacredMQ()

    def register_listener(self):
        """
        Add a new metrics listener.

        The returned object is used to access the recently logged
        metrics values. Once the object is created, it should be
        cleared from time to time using the read_all method.
        Otherwise, its content may grow forever.

        (Alternatively, someone could implement a method that would
        detach the listener from the message queue in order to
        stop new messages from being added)
        """
        return self.mq.add_consumer()

    def log_scalar_metric(self, metric_name, step, value):
        """
        Add a new measurement.

        The measurement will be processed by the MongoDB observer
        during a heartbeat event.

        :param metric_name: The ame of the metric, e.g. training.loss
        :param step: The step number (an integer), e.g. the iteration number
        :param value: The measured value
        """
        self.mq.publish(
            ScalarMetricLogEntry(metric_name, step,
                                 datetime.datetime.utcnow(),
                                 value))


class ScalarMetricLogEntry:
    def __init__(self, name, step, timestamp, value):
        self.name = name
        self.step = step
        self.timestamp = timestamp
        self.value = value


def linearize_metrics(logged_metrics):
    """
    Group metrics by name.

    Takes a list of individual measurements, possibly belonging
    to different metrics and groups them by name.

    :param logged_metrics: A list of ScalarMetricLogEntries
    :return: Measured values grouped by the metric name:
    {"metric_name1": {"steps": [0,1,2], "values": [4, 5, 6],
    "timestamps": [datetime, datetime, datetime]},
    "metric_name2": {...}}
    """
    metrics_by_name = {}
    for metric_entry in logged_metrics:
        if metric_entry.name not in metrics_by_name:
            metrics_by_name[metric_entry.name] = {
                "steps": [],
                "values": [],
                "timestamps": [],
                "name": metric_entry.name
            }
        metrics_by_name[metric_entry.name]["steps"] \
            .append(metric_entry.step)
        metrics_by_name[metric_entry.name]["values"] \
            .append(metric_entry.value)
        metrics_by_name[metric_entry.name]["timestamps"] \
            .append(metric_entry.timestamp)
    return metrics_by_name
