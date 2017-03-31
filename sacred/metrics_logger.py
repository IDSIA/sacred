#!/usr/bin/env python
# coding=utf-8
import datetime

from sacred import messagequeue as mq


class MetricsLogger:
    """MetricsLogger is a part of the Sacred Metrics API"""
    def __init__(self):
        self.mq = mq.SacredMQ()

    def register_listener(self):
        return self.mq.add_consumer()

    def log_scalar_metric(self, metric_name, step, value):
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
    metrics_by_name = {}
    for metric_entry in logged_metrics:
        if metric_entry.name not in metrics_by_name:
            metrics_by_name[metric_entry.name] = {
                "x": [],
                "y": [],
                "timestamps": [],
                "name": metric_entry.name
            }
        metrics_by_name[metric_entry.name]["x"]\
            .append(metric_entry.step)
        metrics_by_name[metric_entry.name]["y"]\
            .append(metric_entry.value)
        metrics_by_name[metric_entry.name]["timestamps"]\
            .append(metric_entry.timestamp)
    return metrics_by_name
