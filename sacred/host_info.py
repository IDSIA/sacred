#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import multiprocessing
import platform
import re
import subprocess
import pkg_resources


def get_processor_name():
    if platform.system() == "Windows":
        return platform.processor().strip()
    elif platform.system() == "Darwin":
        import os
        os.environ['PATH'] = os.environ['PATH'] + os.pathsep + '/usr/sbin'
        command = "sysctl -n machdep.cpu.brand_string"
        return subprocess.check_output(command).strip()
    elif platform.system() == "Linux":
        command = "cat /proc/cpuinfo"
        all_info = subprocess.check_output(command, shell=True).strip()
        for line in all_info.split("\n"):
            if "model name" in line:
                return re.sub(".*model name.*:", "", line, 1).strip()
    return ""


def get_host_info():
    return {
        "cpu": get_processor_name(),
        "cpu_count": multiprocessing.cpu_count(),
        "hostname": platform.node(),
        "os": platform.system(),
        "os_info": platform.platform(),
        "python_version": platform.python_version(),
        "python_compiler": platform.python_compiler()
    }


def get_module_versions(globs):
    module = type(platform)
    module_candidates = set()
    for k, g in globs.items():
        if isinstance(g, module):
            module_candidates.add(g.__name__)
        elif hasattr(g, '__module__'):
            split_m = g.__module__.split('.')
            module_candidates |= {'.'.join(split_m[:i])
                                  for i in range(1, len(split_m)+1)}

    version_info = {}
    for m in module_candidates:
        try:
            version = pkg_resources.get_distribution(m).version
            version_info[m] = version
        except pkg_resources.DistributionNotFound:
            pass

    return version_info