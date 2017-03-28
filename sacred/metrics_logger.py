#!/usr/bin/env python
# coding=utf-8
import datetime
from sacred import messagequeue as mq


class MetricsLogger:

    def __init__(self):
        self.mq = mq.SacredMQ()

    def register_listener(self):
        return self.mq.add_consumer()

    def log_scalar_metric(self, metric_name, timestep, value):
        log_entry = {
            "name": metric_name,
            "type": "scalar",
            "timestep": timestep,
            "value": value,
            "timestamp": datetime.datetime.utcnow()
        }
        self.mq.publish(log_entry)
