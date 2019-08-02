#!/usr/bin/env python
# coding=utf-8
"""This module helps to collect information about the host of an experiment."""

import os
import platform
import re
import subprocess
from xml.etree import ElementTree

import cpuinfo

from sacred.settings import SETTINGS

__all__ = ('get_host_info',)


class IgnoreHostInfo(Exception):
    """Used by host_info_getters to signal that this cannot be gathered."""


def get_host_info():
    """Collect some information about the machine this experiment runs on.

    Returns
    -------
    dict
        A dictionary with information about the CPU, the OS and the
        Python version of this machine.

    """
    host_info = {}
    for k, v in host_info_gatherers.items():
        try:
            host_info[k] = v()
        except IgnoreHostInfo:
            pass
    return host_info


# #################### Default Host Information ###############################

def _hostname():
    return platform.node()


def _os():
    return [platform.system(), platform.platform()]


def _python_version():
    return platform.python_version()


def _cpu():
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


def _gpus():
    if not SETTINGS.HOST_INFO.INCLUDE_GPU_INFO:
        return

    try:
        xml = subprocess.check_output(['nvidia-smi', '-q', '-x']).decode()
    except (FileNotFoundError, OSError, subprocess.CalledProcessError):
        raise IgnoreHostInfo()

    gpu_info = {'gpus': []}
    for child in ElementTree.fromstring(xml):
        if child.tag == 'driver_version':
            gpu_info['driver_version'] = child.text
        if child.tag != 'gpu':
            continue
        gpu = {
            'model': child.find('product_name').text,
            'total_memory': int(child.find('fb_memory_usage').find('total')
                                .text.split()[0]),
            'persistence_mode': (child.find('persistence_mode').text ==
                                 'Enabled')
        }
        gpu_info['gpus'].append(gpu)

    return gpu_info


def _environment():
    keys_to_capture = SETTINGS.HOST_INFO.CAPTURED_ENV
    return {k: os.environ[k] for k in keys_to_capture if k in os.environ}


host_info_gatherers = {'hostname': _hostname,
                       'os': _os,
                       'python_version': _python_version,
                       'cpu': _cpu,
                       'gpus': _gpus,
                       'ENV': _environment}
"""Global dict of functions that are used to collect the host information."""

# ################### Get CPU Information ###############################


def _get_cpu_by_sysctl():
    os.environ['PATH'] += ':/usr/sbin'
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
    return cpuinfo.get_cpu_info().get('brand', 'Unknown')
