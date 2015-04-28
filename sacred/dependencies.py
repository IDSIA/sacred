#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import functools
import hashlib
import os.path
import re
import sys

import pkg_resources
import six
import sacred.optional as opt
from sacred.utils import is_subdir, iter_prefixes

__sacred__ = True  # marks files that should be filtered from stack traces

MB = 1048576
MODULE_BLACKLIST = {None, '__future__', 'hashlib', 'os', 're'} | \
    set(sys.builtin_module_names)
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


def get_py_file_if_possible(pyc_name):
    if pyc_name.endswith('.py'):
        return pyc_name
    assert pyc_name.endswith('.pyc')
    non_compiled_file = pyc_name[:-1]
    if os.path.exists(non_compiled_file):
        return non_compiled_file
    return pyc_name


def get_digest(filename):
        h = hashlib.md5()
        with open(filename, 'rb') as f:
            data = f.read(1 * MB)
            while data:
                h.update(data)
                data = f.read(1 * MB)
        return h.hexdigest()


@functools.total_ordering
class Source(object):
    def __init__(self, filename, digest):
        self.filename = filename
        self.digest = digest

    @staticmethod
    def create(filename):
        if not filename or not os.path.exists(filename):
            raise ValueError('invalid filename or file not found "{}"'
                             .format(filename))

        mainfile = get_py_file_if_possible(os.path.abspath(filename))

        return Source(mainfile, get_digest(mainfile))

    def to_tuple(self):
        return self.filename, self.digest

    def __hash__(self):
        return hash(self.filename)

    def __eq__(self, other):
        if isinstance(other, Source):
            return self.filename == other.filename
        else:
            return False

    def __le__(self, other):
        return self.filename.__le__(other.filename)

    def __repr__(self):
        return '<Source: {}>'.format(self.filename)


@functools.total_ordering
class PackageDependency(object):
    def __init__(self, name, version):
        self.name = name
        self.version = version

    def fill_missing_version(self):
        if self.version is not None:
            return
        try:
            self.version = pkg_resources.get_distribution(self.name).version
        except pkg_resources.DistributionNotFound:
            self.version = '<unknown>'

    def to_tuple(self):
        return self.name, self.version

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, PackageDependency):
            return self.name == other.name
        else:
            return False

    def __le__(self, other):
        return self.name.__le__(other.name)

    def __repr__(self):
        return '<PackageDependency: {}>={}>'.format(self.name, self.version)

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
    def create(mod):
        modname = mod.__name__
        version = PackageDependency.get_version_heuristic(mod)
        return PackageDependency(modname, version)


def create_source_or_dep(modname, mod, dependencies, sources, experiment_path):
    if modname in MODULE_BLACKLIST or modname in dependencies:
        return

    filename = os.path.abspath(mod.__file__) if mod is not None else ''
    if filename and filename not in sources and \
            is_local_source(filename, modname, experiment_path):
        s = Source.create(filename)
        sources.add(s)
    elif mod is not None:
        pdep = PackageDependency.create(mod)
        if pdep.name.find('.') == -1 or pdep.version is not None:
            dependencies.add(pdep)


# Credit to Trent Mick from here:
# https://www.safaribooksonline.com/library/view/python-cookbook/0596001673/ch04s16.html
def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:  # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


def get_relevant_path_parts(path):
    path_parts = splitall(path)
    if path_parts[-1] in ['__init__.py', '__init__.pyc']:
        path_parts = path_parts[:-1]
    else:
        path_parts[-1], ext = os.path.splitext(path_parts[-1])
    return path_parts


def is_local_source(filename, modname, experiment_path):
    if not is_subdir(filename, experiment_path):
        return False
    rel_path = os.path.relpath(filename, experiment_path)
    path_parts = get_relevant_path_parts(rel_path)

    mod_parts = modname.split('.')
    if path_parts == mod_parts:
        return True
    if len(path_parts) > len(mod_parts):
        return False
    abs_path_parts = get_relevant_path_parts(os.path.abspath(filename))
    return all([p == m for p, m in zip(reversed(abs_path_parts),
                                       reversed(mod_parts))])


def gather_sources_and_dependencies(globs):
    dependencies = set()
    main = Source.create(globs.get('__file__'))
    sources = {main}
    experiment_path = os.path.dirname(main.filename)
    for glob in globs.values():
        if isinstance(glob, module):
            mod_path = glob.__name__
        elif hasattr(glob, '__module__'):
            mod_path = glob.__module__
        else:
            continue

        for modname in iter_prefixes(mod_path):
            mod = sys.modules.get(modname)
            create_source_or_dep(modname, mod, dependencies, sources,
                                 experiment_path)

    if opt.has_numpy:
        # Add numpy as a dependency because it might be used for randomness
        dependencies.add(PackageDependency.create(opt.np))

    return sources, dependencies
