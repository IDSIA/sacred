#!/usr/bin/env python
# coding=utf-8
from __future__ import annotations
from dataclasses import dataclass, field

import datetime
from typing import Any
import sacred.optional as opt

from queue import Queue


class MetricsLogger:
    """MetricsLogger collects metrics measured during experiments.

    MetricsLogger is the (only) part of the Metrics API.
    An instance of the class should be created for the Run class, such that the
    log_scalar_metric method is accessible from running experiments using
    _run.metrics.log_scalar_metric.
    """

    def __init__(self):
        self.metrics: dict[str, Metric] = {}
        self._metric_step_counter: dict[str, int | float] = {}
        """Remembers the last number of each metric."""
        self.plugins: list[MetricPlugin] = [PintMetricPlugin(), NumpyMetricPlugin()]

    def log_scalar_metric(
        self,
        metric_name: str,
        value: Any,
        step: int | float = None,
    ):
        """Add a new measurement.

        The measurement will be processed by supported observers
        during the heartbeat event.

        Parameters
        ----------
        metric_name : str
            The name of the metric, e.g. training.loss.
        value : Any
            The measured value. If the value is a `pint.Quantity` then units
            information will be sent to the observer.
        step : int | float, optional
            The step number, e.g. the iteration number
            If not specified, an internal counter for each metric
            is used, incremented by one. By default None
        """
        if step is None:
            step = self._metric_step_counter.get(metric_name, -1) + 1
        self._metric_step_counter[metric_name] = step
        metric_log_entry = ScalarMetricLogEntry(step, datetime.datetime.utcnow(), value)
        if metric_name not in self.metrics:
            self.metrics[metric_name] = Metric(metric_name)
        for plugin in self.plugins:
            plugin.process_metric(metric_log_entry, self.metrics[metric_name])
        self.metrics[metric_name].entries.put(metric_log_entry)

    def get_last_metrics(self) -> list[MetricLogEntry]:
        """Read all measurement events since last call of the method.

        Returns
        -------
        list[MetricLogEntry]
        """
        last_metrics = [
            metric.prepare_for_observers() for metric in self.metrics.values()
        ]
        return [metric for metric in last_metrics if len(metric.entries) > 0]


@dataclass
class ScalarMetricLogEntry:
    """Container for measurements of scalar metrics.

    There is exactly one ScalarMetricLogEntry per logged scalar metric value.
    """

    step: Any
    timestamp: datetime.datetime
    value: Any


@dataclass
class Metric:
    """Container for metric metadat and log entries."""

    name: str
    meta: dict = field(default_factory=dict)
    entries: Queue[ScalarMetricLogEntry] = field(default_factory=Queue)

    def prepare_for_observers(self) -> MetricLogEntry:
        """Captures the current state of the queue for injestion by observers.

        Note that this will clear the entries queue.

        Returns
        -------
        MetricLogEntry
            Same as metric, but with the current state of the queue rendered as a tuple.
        """
        return MetricLogEntry(
            self.name,
            self.meta,
            (self.entries.get_nowait() for _ in self.entries.qsize()),
        )


@dataclass
class MetricLogEntry(Metric):
    """Metric with entries frozen."""

    entries: tuple[ScalarMetricLogEntry]


def linearize_metrics(
    logged_metrics: list[MetricLogEntry],
) -> dict[str, dict[str, list | dict]]:
    """Group metrics by name.

    Takes a list of individual measurements, possibly belonging
    to different metrics and groups them by name.

    Parameters
    ----------
    logged_metrics : list[ScalarMetricLogEntry]

    Returns
    -------
    dict[str, dict[str, list | dict]]
        Measured values grouped by the metric name:
        {
            "metric_name1": {
                "steps": [0,1,2],
                "values": [4, 5, 6],
                "timestamps": [datetime, datetime, datetime],
                "meta": {}
            },
            "metric_name2": {...}
        }
    """
    return {
        metric.name: {
            "meta": metric.meta,
            "steps": [m.step for m in metric.entries],
            "values": [m.value for m in metric.entries],
            "timestamps": [m.timestamp for m in metric.entries],
        }
        for metric in logged_metrics
    }


class MetricPlugin:
    @staticmethod
    def process_metric(metric_entry: ScalarMetricLogEntry, metric: Metric):
        """Transforms `metric_entry` and `metric`.

        Parameters
        ----------
        metric_entry : ScalarMetricLogEntry
        metric : Metric
        """


class NumpyMetricPlugin(MetricPlugin):
    """Convert numpy types to plain python types."""

    @staticmethod
    def process_metric(metric_entry: ScalarMetricLogEntry, metric: Metric):
        if not opt.has_numpy:
            return metric_entry, metric
        import numpy as np

        if isinstance(metric_entry.value, np.generic):
            metric_entry.value = metric_entry.value.item()
        if isinstance(metric_entry.step, np.generic):
            metric_entry.step = metric_entry.step.item()


class PintMetricPlugin(MetricPlugin):
    """Convert pint types to python types, track units, and convert between units."""

    @staticmethod
    def process_metric(
        metric_entry: ScalarMetricLogEntry, metric: Metric
    ) -> tuple[ScalarMetricLogEntry, Metric]:
        if not opt.has_pint:
            return metric_entry, metric
        import pint

        units = metric.meta["units"] if "units" in metric.meta else None
        if isinstance(metric_entry.value, pint.Quantity):
            if units is not None:
                metric_entry.value.to(units)
            else:
                metric.meta["units"] = str(metric_entry.value.units)
            metric_entry.value = metric_entry.value.magnitude
