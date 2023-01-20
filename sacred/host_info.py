"""Helps to collect information about the host of an experiment."""

import os
import platform
import re
import subprocess
from xml.etree import ElementTree
import warnings
from typing import List

import cpuinfo

from sacred.utils import optional_kwargs_decorator
from sacred.settings import SETTINGS

__all__ = ("host_info_gatherers", "get_host_info", "host_info_getter")

# Legacy global dict of functions that are used
# to collect the host information.
host_info_gatherers = {}


class IgnoreHostInfo(Exception):
    """Used by host_info_getters to signal that this cannot be gathered."""


class HostInfoGetter:
    def __init__(self, getter_function, name):
        self.getter_function = getter_function
        self.name = name

    def __call__(self):
        return self.getter_function()

    def get_info(self):
        return self.getter_function()


def host_info_gatherer(name):
    def wrapper(f):
        return HostInfoGetter(f, name)

    return wrapper


def check_additional_host_info(additional_host_info: List[HostInfoGetter]):
    names_taken = [x.name for x in _host_info_gatherers_list]
    for getter in additional_host_info:
        if getter.name in names_taken:
            error_msg = (
                "Key {} used in `additional_host_info` already exists as a "
                "default gatherer function. Do not use the following keys: "
                "{}"
            ).format(getter.name, names_taken)
            raise KeyError(error_msg)


def get_host_info(additional_host_info: List[HostInfoGetter] = None):
    """Collect some information about the machine this experiment runs on.

    Returns
    -------
    dict
        A dictionary with information about the CPU, the OS and the
        Python version of this machine.

    """
    additional_host_info = additional_host_info or []
    # can't use += because we don't want to modify the mutable argument.
    additional_host_info = additional_host_info + _host_info_gatherers_list
    all_host_info_gatherers = host_info_gatherers.copy()
    for getter in additional_host_info:
        all_host_info_gatherers[getter.name] = getter
    host_info = {}
    for k, v in all_host_info_gatherers.items():
        try:
            host_info[k] = v()
        except IgnoreHostInfo:
            pass
    return host_info


@optional_kwargs_decorator
def host_info_getter(func, name=None):
    """
    The decorated function is added to the process of collecting the host_info.

    This just adds the decorated function to the global
    ``sacred.host_info.host_info_gatherers`` dictionary.
    The functions from that dictionary are used when collecting the host info
    using :py:func:`~sacred.host_info.get_host_info`.

    Parameters
    ----------
    func : callable
        A function that can be called without arguments and returns some
        json-serializable information.
    name : str, optional
        The name of the corresponding entry in host_info.
        Defaults to the name of the function.

    Returns
    -------
    The function itself.

    """
    warnings.warn(
        "The host_info_getter is deprecated. "
        "Please use the `additional_host_info` argument"
        " in the Experiment constructor.",
        DeprecationWarning,
    )
    name = name or func.__name__
    host_info_gatherers[name] = func
    return func


# #################### Default Host Information ###############################


@host_info_gatherer(name="hostname")
def _hostname():
    return platform.node()


@host_info_gatherer(name="os")
def _os():
    return [platform.system(), platform.platform()]


@host_info_gatherer(name="python_version")
def _python_version():
    return platform.python_version()


@host_info_gatherer(name="cpu")
def _cpu():
    if not SETTINGS.HOST_INFO.INCLUDE_CPU_INFO:
        return

    if platform.system() == "Windows":
        return _get_cpu_by_pycpuinfo()
    try:
        if platform.system() == "Darwin":
            return _get_cpu_by_sysctl()
        elif platform.system() == "Linux":
            return _get_cpu_by_proc_cpuinfo()
    except Exception:
        # Use pycpuinfo only if other ways fail, since it takes about 1 sec
        return _get_cpu_by_pycpuinfo()


@host_info_gatherer(name="gpus")
def _gpus():
    if not SETTINGS.HOST_INFO.INCLUDE_GPU_INFO:
        return

    try:
        xml = subprocess.check_output(["nvidia-smi", "-q", "-x"]).decode(
            "utf-8", "replace"
        )
    except (FileNotFoundError, OSError, subprocess.CalledProcessError) as e:
        raise IgnoreHostInfo() from e

    gpu_info = {"gpus": []}
    for child in ElementTree.fromstring(xml):
        if child.tag == "driver_version":
            gpu_info["driver_version"] = child.text
        if child.tag != "gpu":
            continue
        fb_memory_usage = child.find("fb_memory_usage").find("total").text
        if fb_memory_usage == "Insufficient Permissions":
            # for Multi-Instance GPU (MIG) instances
            mig = child.find("mig_devices").find("mig_device")
            fb_memory_usage = mig.find("fb_memory_usage").find("total").text
        gpu = {
            "model": child.find("product_name").text,
            "total_memory": int(fb_memory_usage.split()[0]),
            "persistence_mode": (child.find("persistence_mode").text == "Enabled"),
        }
        gpu_info["gpus"].append(gpu)

    return gpu_info


@host_info_gatherer(name="ENV")
def _environment():
    keys_to_capture = SETTINGS.HOST_INFO.CAPTURED_ENV
    return {k: os.environ[k] for k in keys_to_capture if k in os.environ}


_host_info_gatherers_list = [_hostname, _os, _python_version, _cpu, _gpus, _environment]

# ################### Get CPU Information ###############################


def _get_cpu_by_sysctl():
    os.environ["PATH"] += ":/usr/sbin"
    command = ["sysctl", "-n", "machdep.cpu.brand_string"]
    return subprocess.check_output(command).decode().strip()


def _get_cpu_by_proc_cpuinfo():
    command = ["cat", "/proc/cpuinfo"]
    all_info = subprocess.check_output(command).decode()
    model_pattern = re.compile(r"^\s*model name\s*:")
    for line in all_info.split("\n"):
        if model_pattern.match(line):
            return model_pattern.sub("", line, 1).strip()


def _get_cpu_by_pycpuinfo():
    return cpuinfo.get_cpu_info().get("brand_raw", "Unknown")
