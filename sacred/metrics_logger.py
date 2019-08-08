#!/usr/bin/env python
# coding=utf-8
import datetime
import sacred.optional as opt

from queue import Queue, Empty


class MetricsLogger:
    """MetricsLogger collects metrics measured during experiments.

    MetricsLogger is the (only) part of the Metrics API.
    An instance of the class should be created for the Run class, such that the
    log_scalar_metric method is accessible from running experiments using
    _run.metrics.log_scalar_metric.
    """

    def __init__(self):
        # Create a message queue that remembers
        # calls of the log_scalar_metric
        self._logged_metrics = Queue()
        self._metric_step_counter = {}
        """Remembers the last number of each metric."""

    def log_scalar_metric(self, metric_name, value, step=None):
        """
        Add a new measurement.

        The measurement will be processed by the MongoDB observer
        during a heartbeat event.
        Other observers are not yet supported.

        :param metric_name: The name of the metric, e.g. training.loss.
        :param value: The measured value.
        :param step: The step number (integer), e.g. the iteration number
                    If not specified, an internal counter for each metric
                    is used, incremented by one.
        """
        if opt.has_numpy:
            np = opt.np
            if isinstance(value, np.generic):
                value = value.item()
            if isinstance(step, np.generic):
                step = step.item()
        if step is None:
            step = self._metric_step_counter.get(metric_name, -1) + 1
        self._logged_metrics.put(
            ScalarMetricLogEntry(metric_name, step, datetime.datetime.utcnow(), value)
        )
        self._metric_step_counter[metric_name] = step

    def get_last_metrics(self):
        """Read all measurement events since last call of the method.

        :return List[ScalarMetricLogEntry]
        """
        read_up_to = self._logged_metrics.qsize()
        messages = []
        for i in range(read_up_to):
            try:
                messages.append(self._logged_metrics.get_nowait())
            except Empty:
                pass
        return messages


class ScalarMetricLogEntry:
    """Container for measurements of scalar metrics.

    There is exactly one ScalarMetricLogEntry per logged scalar metric value.
    """

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
                "name": metric_entry.name,
            }
        metrics_by_name[metric_entry.name]["steps"].append(metric_entry.step)
        metrics_by_name[metric_entry.name]["values"].append(metric_entry.value)
        metrics_by_name[metric_entry.name]["timestamps"].append(metric_entry.timestamp)
    return metrics_by_name
