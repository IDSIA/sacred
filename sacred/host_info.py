#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import multiprocessing
import platform
import re
import subprocess
import sys
import pkg_resources

try:
    isinstance("", basestring)  # attempt to evaluate basestring

    def is_str(obj):
        return isinstance(obj, basestring)
except NameError:
    def is_str(obj):
        return isinstance(obj, str)


def get_processor_name():
    if platform.system() == "Windows":
        return platform.processor().strip()
    elif platform.system() == "Darwin":
        import os
        os.environ['PATH'] = os.environ['PATH'] + os.pathsep + '/usr/sbin'
        command = ["sysctl", "-n", "machdep.cpu.brand_string"]
        return subprocess.check_output(command).strip()
    elif platform.system() == "Linux":
        command = ["cat", "/proc/cpuinfo"]
        all_info = str(subprocess.check_output(command)).strip()
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

MODULE_BLACKLIST = {None, '__future__'} | set(sys.builtin_module_names)
module = type(platform)


def get_dependencies(globs):
    dependencies = {}

    for glob in globs.values():
        if isinstance(glob, module) and glob.__name__ not in MODULE_BLACKLIST:
            dependencies[glob.__name__] = get_module_version_heuristic(glob)

        elif hasattr(glob, '__module__'):
            modname = glob.__module__.split('.')[0]
            if modname not in MODULE_BLACKLIST and modname not in dependencies:
                dependencies[modname] = get_module_version_heuristic(modname)

    return dependencies


def fill_missing_versions(deps):
    for mod_name, ver in deps.items():
        if ver is None:
            deps[mod_name] = get_version_from_pkg_resources(mod_name)


def get_modules(globs):
    return {g for g in globs.values()
            if isinstance(g, module) and g.__name__ not in MODULE_BLACKLIST}


PEP440_VERSION_PATTERN = re.compile(r"""
^
(\d+!)?              # epoch
(\d[\.\d]*(?<= \d))  # release
((?:[abc]|rc)\d+)?   # pre-release
(?:(\.post\d+))?     # post-release
(?:(\.dev\d+))?      # development release
$
""", flags=re.VERBOSE)


def get_module_version_heuristic(mod):
    if not isinstance(mod, module):
        mod = sys.modules.get(mod)
        if not mod:
            return None
    possible_version_attributes = {'version', 'VERSION', '__version__'}
    for vattr in possible_version_attributes:
        if not hasattr(mod, vattr):
            continue
        version = getattr(mod, vattr)
        if is_str(version) and PEP440_VERSION_PATTERN.match(version):
            return version
    return None


def get_version_from_pkg_resources(mod_name):
    try:
        return pkg_resources.get_distribution(mod_name).version
    except pkg_resources.DistributionNotFound:
        return None
