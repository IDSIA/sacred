#!/usr/bin/env python
# coding=utf-8
from __future__ import annotations
from dataclasses import dataclass

import datetime
from typing import Any
import sacred.optional as opt

from queue import Queue, Empty
import pint


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
        :param value: The measured value. If the value is a `pint.Quantity` then units
                    information will be sent to the observer.
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
        for _ in range(read_up_to):
            try:
                messages.append(self._logged_metrics.get_nowait())
            except Empty:
                pass
        return messages


@dataclass
class ScalarMetricLogEntry:
    """Container for measurements of scalar metrics.

    There is exactly one ScalarMetricLogEntry per logged scalar metric value.
    """

    name: str
    step: Any
    timestamp: datetime.datetime
    value: Any


def linearize_metrics(
    logged_metrics: list[ScalarMetricLogEntry],
) -> dict[str, dict[str, list]]:
    """Group metrics by name.

    Takes a list of individual measurements, possibly belonging
    to different metrics and groups them by name.

    Parameters
    ----------
    logged_metrics : list[ScalarMetricLogEntry]

    Returns
    -------
    dict[str, dict[str, list]]
        Measured values grouped by the metric name:
        {
            "metric_name1": {
                "steps": [0,1,2],
                "values": [4, 5, 6],
                "timestamps": [datetime, datetime, datetime],
                units: "meter"
            },
            "metric_name2": {...}
        }

    Raises
    ------
    MetricLinearizationError
        A metric has been logged with incompatible units.
    """
    metrics_by_name: dict[str, dict[str, list]] = {}
    for metric_entry in logged_metrics:
        if metric_entry.name not in metrics_by_name:
            metrics_by_name[metric_entry.name] = {
                "steps": [],
                "values": [],
                "timestamps": [],
                "name": metric_entry.name,
                "units": None,
            }
        metrics_by_name[metric_entry.name]["steps"].append(metric_entry.step)
        try:
            magnitude, units = linearize_value(
                metric_entry.value, metrics_by_name[metric_entry.name]["units"]
            )
        except pint.DimensionalityError as exc:
            raise MetricLinearizationError(metric_entry) from exc
        metrics_by_name[metric_entry.name]["values"].append(magnitude)
        metrics_by_name[metric_entry.name]["units"] = units
        metrics_by_name[metric_entry.name]["timestamps"].append(metric_entry.timestamp)
    return metrics_by_name


def linearize_value(
    value: Any | pint.Quantity, expected_units: str | None
) -> tuple[Any, str | None]:
    """Converts `value` to `expected_units` and breaks it into tuple of `(magnitude, units_str)`.

    Parameters
    ----------
    value : Any | pint.Quantity
        Value to linearize
    expected_units : str | None
        Units to convert to (if any)

    Returns
    -------
    tuple[Any, str | None]
        (magnitude, units_str)
    """
    if not isinstance(value, pint.Quantity):
        return value, None
    if expected_units is not None:
        value = value.to(expected_units)
    if opt.has_numpy:
        np = opt.np
        if isinstance(value.magnitude, np.generic):
            return value.magnitude.item(), str(value.units)
    return value.magnitude, str(value.units)


class MetricLinearizationError(Exception):
    """Error thrown when a metric cannot be linearized."""

    def __init__(self, metric: ScalarMetricLogEntry):
        self.metric = metric

    def __str__(self) -> str:
        return f"Error while linearizing {self.metric}"
