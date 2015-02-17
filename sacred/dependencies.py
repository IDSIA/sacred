#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import hashlib
import os.path
import sys
import re
import pkg_resources
import six

# PackageDependency = namedtuple("PackageDepenency", "packagename,version")
# FileDependency = namedtuple("FileDependency", 'filename,sha256')

MB = 1048576
MODULE_BLACKLIST = {None, '__future__'} | set(sys.builtin_module_names)
module = type(sys)
PEP440_VERSION_PATTERN = re.compile(r"""
^
(\d+!)?              # epoch
(\d[\.\d]*(?<= \d))  # release
((?:[abc]|rc)\d+)?   # pre-release
(?:(\.post\d+))?     # post-release
(?:(\.dev\d+))?      # development release
$
""", flags=re.VERBOSE)


class FileDependency(object):
    def __init__(self, filename, digest):
        self.filename = filename
        self.digest = digest

    @staticmethod
    def get_digest(filename):
        h = hashlib.sha256()
        with open(filename, 'rb') as f:
            data = f.read(1 * MB)
            while data:
                h.update(data)
                data = f.read(1 * MB)
        return h.hexdigest()

    @staticmethod
    def create(filename):
        if not filename:
            return FileDependency('', '')

        mainfile = os.path.abspath(filename)
        if mainfile.endswith('.pyc'):
            non_compiled_mainfile = mainfile[:-1]
            if os.path.exists(non_compiled_mainfile):
                mainfile = non_compiled_mainfile

        return FileDependency(mainfile, FileDependency.get_digest(mainfile))


class PackageDependency(object):
    def __init__(self, name, version):
        self.name = name
        self.version = version

    @staticmethod
    def get_version_heuristic(mod):
        possible_version_attributes = ['__version__', 'VERSION', 'version']
        for vattr in possible_version_attributes:
            if hasattr(mod, vattr):
                version = getattr(mod, vattr)
                if isinstance(version, six.string_types) and \
                        PEP440_VERSION_PATTERN.match(version):
                    return version
                if isinstance(version, tuple):
                    version = '.'.join([str(n) for n in version])
                    if PEP440_VERSION_PATTERN.match(version):
                        return version

        return None

    @staticmethod
    def create(mod_or_name):
        if isinstance(mod_or_name, module):
            mod = mod_or_name
        else:
            mod = sys.modules.get(mod_or_name)

        if not mod:
            return None

        modname = mod.__name__
        version = PackageDependency.get_version_heuristic(mod)

        return PackageDependency(modname, version)



def get_dependencies(globs):
    dependencies = {}

    for glob in globs.values():
        if isinstance(glob, module) and glob.__name__ not in MODULE_BLACKLIST:
            dependencies[glob.__name__] = PackageDependency.get_version_heuristic(glob)

        elif hasattr(glob, '__module__'):
            modname = glob.__module__.split('.')[0]
            if modname not in MODULE_BLACKLIST and modname not in dependencies:
                dependencies[modname] = PackageDependency.get_version_heuristic(modname)

    return dependencies


def fill_missing_versions(deps):
    for mod_name, ver in deps.items():
        if ver is None:
            deps[mod_name] = get_version_from_pkg_resources(mod_name)


def get_modules(globs):
    return {g for g in globs.values()
            if isinstance(g, module) and g.__name__ not in MODULE_BLACKLIST}





def get_version_from_pkg_resources(mod_name):
    try:
        return pkg_resources.get_distribution(mod_name).version
    except pkg_resources.DistributionNotFound:
        return None
