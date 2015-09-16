#!/usr/bin/env python
# coding=utf-8
"""This module helps to collect information about the host of an experiment."""
from __future__ import division, print_function, unicode_literals

import multiprocessing
import os
import platform
import re
import subprocess

__sacred__ = True  # marks files that should be filtered from stack traces


def get_host_info():
    """Collect some information about the machine this experiment runs on.

    :return: A dictionary with information about the CPU, the OS and the
             Python version of this machine.
    :rtype: dict
    """
    return {
        "cpu": _get_processor_name(),
        "cpu_count": multiprocessing.cpu_count(),
        "hostname": platform.node(),
        "os": platform.system(),
        "os_info": platform.platform(),
        "python_version": platform.python_version(),
        "python_compiler": platform.python_compiler()
    }


def _get_processor_name():
    if platform.system() == "Windows":
        return platform.processor().strip()
    elif platform.system() == "Darwin":
        os.environ['PATH'] = os.environ['PATH'] + os.pathsep + '/usr/sbin'
        command = ["sysctl", "-n", "machdep.cpu.brand_string"]
        return subprocess.check_output(command).decode().strip()
    elif platform.system() == "Linux":
        command = ["cat", "/proc/cpuinfo"]
        all_info = subprocess.check_output(command).decode()
        model_pattern = re.compile("^\s*model name\s*:")
        for line in all_info.split("\n"):
            if model_pattern.match(line):
                return model_pattern.sub("", line, 1).strip()
