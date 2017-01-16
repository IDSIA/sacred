#!/usr/bin/env python
# coding=utf-8
"""This module helps to collect information about the host of an experiment."""
from __future__ import division, print_function, unicode_literals

import os
import platform
import re
import subprocess
import xml.etree.ElementTree as ET
from sacred.utils import optional_kwargs_decorator, FileNotFoundError
from sacred.settings import SETTINGS

__sacred__ = True  # marks files that should be filtered from stack traces

__all__ = ('host_info_gatherers', 'get_host_info', 'host_info_getter')

host_info_gatherers = {}
"""Global dict of functions that are used to collect the host information."""


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
    name = name or func.__name__
    host_info_gatherers[name] = func
    return func


# #################### Default Host Information ###############################

@host_info_getter(name='hostname')
def _hostname():
    return platform.node()


@host_info_getter(name='os')
def _os():
    return [platform.system(), platform.platform()]


@host_info_getter(name='python_version')
def _python_version():
    return platform.python_version()


@host_info_getter(name='cpu')
def _cpu():
    if platform.system() == "Windows":
        return platform.processor().strip()
    elif platform.system() == "Darwin":
        os.environ['PATH'] += ':/usr/sbin'
        command = ["sysctl", "-n", "machdep.cpu.brand_string"]
        return subprocess.check_output(command).decode().strip()
    elif platform.system() == "Linux":
        command = ["cat", "/proc/cpuinfo"]
        all_info = subprocess.check_output(command).decode()
        model_pattern = re.compile("^\s*model name\s*:")
        for line in all_info.split("\n"):
            if model_pattern.match(line):
                return model_pattern.sub("", line, 1).strip()


if SETTINGS.HOST_INFO.INCLUDE_GPU_INFO:
    @host_info_getter(name='gpus')
    def _gpus():
        try:
            xml = subprocess.check_output(['nvidia-smi', '-q', '-x']).decode()
        except (FileNotFoundError, OSError, subprocess.CalledProcessError):
            raise IgnoreHostInfo()

        gpu_info = {'gpus': []}
        for child in ET.fromstring(xml):
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
