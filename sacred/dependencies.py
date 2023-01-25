#!/usr/bin/env python
# coding=utf-8

import functools
import hashlib
import os.path
import re
import sys
from pathlib import Path

import pkg_resources

import sacred.optional as opt
from sacred import SETTINGS
from sacred.utils import iter_prefixes

MB = 1048576
MODULE_BLACKLIST = set(sys.builtin_module_names)
# sadly many builtins are missing from the above, so we list them manually:
MODULE_BLACKLIST |= {
    None,
    "__future__",
    "_abcoll",
    "_bootlocale",
    "_bsddb",
    "_bz2",
    "_codecs_cn",
    "_codecs_hk",
    "_codecs_iso2022",
    "_codecs_jp",
    "_codecs_kr",
    "_codecs_tw",
    "_collections_abc",
    "_compat_pickle",
    "_compression",
    "_crypt",
    "_csv",
    "_ctypes",
    "_ctypes_test",
    "_curses",
    "_curses_panel",
    "_dbm",
    "_decimal",
    "_dummy_thread",
    "_elementtree",
    "_gdbm",
    "_hashlib",
    "_hotshot",
    "_json",
    "_lsprof",
    "_LWPCookieJar",
    "_lzma",
    "_markupbase",
    "_MozillaCookieJar",
    "_multibytecodec",
    "_multiprocessing",
    "_opcode",
    "_osx_support",
    "_pydecimal",
    "_pyio",
    "_sitebuiltins",
    "_sqlite3",
    "_ssl",
    "_strptime",
    "_sysconfigdata",
    "_sysconfigdata_m",
    "_sysconfigdata_nd",
    "_testbuffer",
    "_testcapi",
    "_testimportmultiple",
    "_testmultiphase",
    "_threading_local",
    "_tkinter",
    "_weakrefset",
    "abc",
    "aifc",
    "antigravity",
    "anydbm",
    "argparse",
    "ast",
    "asynchat",
    "asyncio",
    "asyncore",
    "atexit",
    "audiodev",
    "audioop",
    "base64",
    "BaseHTTPServer",
    "Bastion",
    "bdb",
    "binhex",
    "bisect",
    "bsddb",
    "bz2",
    "calendar",
    "Canvas",
    "CDROM",
    "cgi",
    "CGIHTTPServer",
    "cgitb",
    "chunk",
    "cmath",
    "cmd",
    "code",
    "codecs",
    "codeop",
    "collections",
    "colorsys",
    "commands",
    "compileall",
    "compiler",
    "concurrent",
    "ConfigParser",
    "configparser",
    "contextlib",
    "Cookie",
    "cookielib",
    "copy",
    "copy_reg",
    "copyreg",
    "cProfile",
    "crypt",
    "csv",
    "ctypes",
    "curses",
    "datetime",
    "dbhash",
    "dbm",
    "decimal",
    "Dialog",
    "difflib",
    "dircache",
    "dis",
    "distutils",
    "DLFCN",
    "doctest",
    "DocXMLRPCServer",
    "dumbdbm",
    "dummy_thread",
    "dummy_threading",
    "easy_install",
    "email",
    "encodings",
    "ensurepip",
    "enum",
    "filecmp",
    "FileDialog",
    "fileinput",
    "FixTk",
    "fnmatch",
    "formatter",
    "fpectl",
    "fpformat",
    "fractions",
    "ftplib",
    "functools",
    "future_builtins",
    "genericpath",
    "getopt",
    "getpass",
    "gettext",
    "glob",
    "gzip",
    "hashlib",
    "heapq",
    "hmac",
    "hotshot",
    "html",
    "htmlentitydefs",
    "htmllib",
    "HTMLParser",
    "http",
    "httplib",
    "idlelib",
    "ihooks",
    "imaplib",
    "imghdr",
    "imp",
    "importlib",
    "imputil",
    "IN",
    "inspect",
    "io",
    "ipaddress",
    "json",
    "keyword",
    "lib2to3",
    "linecache",
    "linuxaudiodev",
    "locale",
    "logging",
    "lzma",
    "macpath",
    "macurl2path",
    "mailbox",
    "mailcap",
    "markupbase",
    "md5",
    "mhlib",
    "mimetools",
    "data",
    "MimeWriter",
    "mimify",
    "mmap",
    "modulefinder",
    "multifile",
    "multiprocessing",
    "mutex",
    "netrc",
    "new",
    "nis",
    "nntplib",
    "ntpath",
    "nturl2path",
    "numbers",
    "opcode",
    "operator",
    "optparse",
    "os",
    "os2emxpath",
    "ossaudiodev",
    "parser",
    "pathlib",
    "pdb",
    "pickle",
    "pickletools",
    "pip",
    "pipes",
    "pkg_resources",
    "pkgutil",
    "platform",
    "plistlib",
    "popen2",
    "poplib",
    "posixfile",
    "posixpath",
    "pprint",
    "profile",
    "pstats",
    "pty",
    "py_compile",
    "pyclbr",
    "pydoc",
    "pydoc_data",
    "pyexpat",
    "Queue",
    "queue",
    "quopri",
    "random",
    "re",
    "readline",
    "repr",
    "reprlib",
    "resource",
    "rexec",
    "rfc822",
    "rlcompleter",
    "robotparser",
    "runpy",
    "sched",
    "ScrolledText",
    "selectors",
    "sets",
    "setuptools",
    "sgmllib",
    "sha",
    "shelve",
    "shlex",
    "shutil",
    "signal",
    "SimpleDialog",
    "SimpleHTTPServer",
    "SimpleXMLRPCServer",
    "site",
    "sitecustomize",
    "smtpd",
    "smtplib",
    "sndhdr",
    "socket",
    "SocketServer",
    "socketserver",
    "sqlite3",
    "sre",
    "sre_compile",
    "sre_constants",
    "sre_parse",
    "ssl",
    "stat",
    "statistics",
    "statvfs",
    "string",
    "StringIO",
    "stringold",
    "stringprep",
    "struct",
    "subprocess",
    "sunau",
    "sunaudio",
    "symbol",
    "symtable",
    "sysconfig",
    "tabnanny",
    "tarfile",
    "telnetlib",
    "tempfile",
    "termios",
    "test",
    "textwrap",
    "this",
    "threading",
    "timeit",
    "Tix",
    "tkColorChooser",
    "tkCommonDialog",
    "Tkconstants",
    "Tkdnd",
    "tkFileDialog",
    "tkFont",
    "tkinter",
    "Tkinter",
    "tkMessageBox",
    "tkSimpleDialog",
    "toaiff",
    "token",
    "tokenize",
    "trace",
    "traceback",
    "tracemalloc",
    "ttk",
    "tty",
    "turtle",
    "types",
    "TYPES",
    "typing",
    "unittest",
    "urllib",
    "urllib2",
    "urlparse",
    "user",
    "UserDict",
    "UserList",
    "UserString",
    "uu",
    "uuid",
    "venv",
    "warnings",
    "wave",
    "weakref",
    "webbrowser",
    "wheel",
    "whichdb",
    "wsgiref",
    "xdrlib",
    "xml",
    "xmllib",
    "xmlrpc",
    "xmlrpclib",
    "xxlimited",
    "zipapp",
    "zipfile",
}

module = type(sys)
PEP440_VERSION_PATTERN = re.compile(
    r"""
^
(\d+!)?              # epoch
(\d[.\d]*(?<= \d))   # release
((?:[abc]|rc)\d+)?   # pre-release
(?:(\.post\d+))?     # post-release
(?:(\.dev\d+))?      # development release
$
""",
    flags=re.VERBOSE,
)


def get_py_file_if_possible(pyc_name):
    """Try to retrieve a X.py file for a given X.py[c] file."""
    if pyc_name.endswith((".py", ".so", ".pyd", ".ipynb")):
        return pyc_name
    assert pyc_name.endswith(".pyc")
    non_compiled_file = pyc_name[:-1]
    if os.path.exists(non_compiled_file):
        return non_compiled_file
    return pyc_name


def get_digest(filename):
    """Compute the MD5 hash for a given file."""
    h = hashlib.md5()
    with open(filename, "rb") as f:
        data = f.read(1 * MB)
        while data:
            h.update(data)
            data = f.read(1 * MB)
        return h.hexdigest()


def get_commit_if_possible(filename, save_git_info):
    """Try to retrieve VCS information for a given file.

    Currently only supports git using the gitpython package.

    Parameters
    ----------
    filename : str

    Returns
    -------
        path: str
            The base path of the repository
        commit: str
            The commit hash
        is_dirty: bool
            True if there are uncommitted changes in the repository
    """
    if save_git_info is False:
        return None, None, None

    try:
        from git import Repo, InvalidGitRepositoryError
    except ImportError as e:
        raise ValueError(
            "Cannot import git (pip install GitPython).\n"
            "Either GitPython or the git executable is missing.\n"
            "You can disable git with:\n"
            "    sacred.Experiment(..., save_git_info=False)"
        ) from e

    directory = os.path.dirname(filename)
    try:
        repo = Repo(directory, search_parent_directories=True)
    except InvalidGitRepositoryError:
        return None, None, None
    try:
        path = repo.remote().url
    except ValueError:
        path = "git:/" + repo.working_dir
    is_dirty = repo.is_dirty()
    commit = repo.head.commit.hexsha
    return path, commit, is_dirty


@functools.total_ordering
class Source:
    def __init__(self, filename, digest, repo, commit, isdirty):
        self.filename = os.path.realpath(filename)
        self.digest = digest
        self.repo = repo
        self.commit = commit
        self.is_dirty = isdirty

    @staticmethod
    def create(filename, save_git_info=True):
        if not filename or not os.path.exists(filename):
            raise ValueError('invalid filename or file not found "{}"'.format(filename))

        main_file = get_py_file_if_possible(os.path.abspath(filename))
        repo, commit, is_dirty = get_commit_if_possible(main_file, save_git_info)
        return Source(main_file, get_digest(main_file), repo, commit, is_dirty)

    def to_json(self, base_dir=None):
        if base_dir:
            return (
                os.path.relpath(self.filename, os.path.realpath(base_dir)),
                self.digest,
            )
        else:
            return self.filename, self.digest

    def __hash__(self):
        return hash(self.filename)

    def __eq__(self, other):
        if isinstance(other, Source):
            return self.filename == other.filename
        elif isinstance(other, str):
            return self.filename == other
        else:
            return False

    def __le__(self, other):
        return self.filename.__le__(other.filename)

    def __repr__(self):
        return "<Source: {}>".format(self.filename)


@functools.total_ordering
class PackageDependency:
    modname_to_dist = {}

    def __init__(self, name, version):
        self.name = name
        self.version = version

    def fill_missing_version(self):
        if self.version is not None:
            return
        dist = pkg_resources.working_set.by_key.get(self.name)
        self.version = dist.version if dist else None

    def to_json(self):
        return "{}=={}".format(self.name, self.version or "<unknown>")

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
        return "<PackageDependency: {}={}>".format(self.name, self.version)

    @classmethod
    def create(cls, mod):
        if not cls.modname_to_dist:
            # some packagenames don't match the module names (e.g. PyYAML)
            # so we set up a dict to map from module name to package name
            for dist in pkg_resources.working_set:
                try:
                    toplevel_names = dist._get_metadata("top_level.txt")
                    for tln in toplevel_names:
                        cls.modname_to_dist[tln] = dist.project_name, dist.version
                except Exception:
                    pass

        name, version = cls.modname_to_dist.get(mod.__name__, (mod.__name__, None))

        return PackageDependency(name, version)


def convert_path_to_module_parts(path):
    """Convert path to a python file into list of module names."""
    module_parts = list(path.parts)
    if module_parts[-1] in ["__init__.py", "__init__.pyc"]:
        # remove trailing __init__.py
        module_parts = module_parts[:-1]
    else:
        # remove file extension
        module_parts[-1], _ = os.path.splitext(module_parts[-1])
    return module_parts


def is_local_source(filename, modname, experiment_path):
    """Check if a module comes from the given experiment path.

    Check if a module, given by name and filename, is from (a subdirectory of )
    the given experiment path.
    This is used to determine if the module is a local source file, or rather
    a package dependency.

    Parameters
    ----------
    filename: str
        The absolute filename of the module in question.
        (Usually module.__file__)
    modname: str
        The full name of the module including parent namespaces.
    experiment_path: str
        The base path of the experiment.

    Returns
    -------
    bool:
        True if the module was imported locally from (a subdir of) the
        experiment_path, and False otherwise.
    """
    filename = Path(os.path.abspath(os.path.realpath(filename)))
    experiment_path = Path(os.path.abspath(os.path.realpath(experiment_path)))
    if experiment_path not in filename.parents:
        return False
    rel_path = filename.relative_to(experiment_path)
    path_parts = convert_path_to_module_parts(rel_path)

    mod_parts = modname.split(".")
    if path_parts == mod_parts:
        return True
    if len(path_parts) > len(mod_parts):
        return False
    abs_path_parts = convert_path_to_module_parts(filename)
    return all([p == m for p, m in zip(reversed(abs_path_parts), reversed(mod_parts))])


def get_main_file(globs, save_git_info):
    filename = globs.get("__file__")

    if filename is None:
        experiment_path = os.path.abspath(os.path.curdir)
        main = None
    else:
        main = Source.create(globs.get("__file__"), save_git_info)
        experiment_path = os.path.dirname(main.filename)
    return experiment_path, main


def iterate_imported_modules(globs):
    checked_modules = set(MODULE_BLACKLIST)
    for glob in globs.values():
        if isinstance(glob, module):
            mod_path = glob.__name__
        elif hasattr(glob, "__module__"):
            mod_path = glob.__module__
        else:
            continue  # pragma: no cover

        if not mod_path:
            continue

        for modname in iter_prefixes(mod_path):
            if modname in checked_modules:
                continue
            checked_modules.add(modname)
            mod = sys.modules.get(modname)
            if mod is not None:
                yield modname, mod


def iterate_all_python_files(base_path):
    # TODO support ignored directories/files
    for dirname, subdirlist, filelist in os.walk(base_path):
        if "__pycache__" in dirname:
            continue
        for filename in filelist:
            if filename.endswith(".py"):
                yield os.path.join(base_path, dirname, filename)


def iterate_sys_modules():
    items = list(sys.modules.items())
    for modname, mod in items:
        if modname not in MODULE_BLACKLIST and mod is not None:
            yield modname, mod


def get_sources_from_modules(module_iterator, base_path, save_git_info):
    sources = set()
    for modname, mod in module_iterator:
        # hasattr doesn't work with python extensions
        if not getattr(mod, "__file__", None):
            continue

        filename = os.path.abspath(mod.__file__)
        if filename not in sources and is_local_source(filename, modname, base_path):
            s = Source.create(filename, save_git_info)
            sources.add(s)
    return sources


def get_dependencies_from_modules(module_iterator, base_path):
    dependencies = set()
    for modname, mod in module_iterator:
        # hasattr doesn't work with python extensions
        if getattr(mod, "__file__", None) and is_local_source(
            os.path.abspath(mod.__file__), modname, base_path
        ):
            continue
        if modname.startswith("_") or "." in modname:
            continue

        try:
            pdep = PackageDependency.create(mod)
            if pdep.version is not None:
                dependencies.add(pdep)
        except AttributeError:
            pass
    return dependencies


def get_sources_from_sys_modules(globs, base_path, save_git_info):
    return get_sources_from_modules(iterate_sys_modules(), base_path, save_git_info)


def get_sources_from_imported_modules(globs, base_path, save_git_info):
    return get_sources_from_modules(
        iterate_imported_modules(globs), base_path, save_git_info
    )


def get_sources_from_local_dir(globs, base_path, save_git_info):
    return {
        Source.create(filename, save_git_info)
        for filename in iterate_all_python_files(base_path)
    }


def get_dependencies_from_sys_modules(globs, base_path):
    return get_dependencies_from_modules(iterate_sys_modules(), base_path)


def get_dependencies_from_imported_modules(globs, base_path):
    return get_dependencies_from_modules(iterate_imported_modules(globs), base_path)


def get_dependencies_from_pkg(globs, base_path):
    dependencies = set()
    for dist in pkg_resources.working_set:
        if dist.version == "0.0.0":
            continue  # ugly hack to deal with pkg-resource version bug
        dependencies.add(PackageDependency(dist.project_name, dist.version))
    return dependencies


source_discovery_strategies = {
    "none": lambda *_, **__: set(),
    "imported": get_sources_from_imported_modules,
    "sys": get_sources_from_sys_modules,
    "dir": get_sources_from_local_dir,
}

dependency_discovery_strategies = {
    "none": lambda *_, **__: set(),
    "imported": get_dependencies_from_imported_modules,
    "sys": get_dependencies_from_sys_modules,
    "pkg": get_dependencies_from_pkg,
}


def gather_sources_and_dependencies(globs, save_git_info, base_dir=None):
    """Scan the given globals for modules and return them as dependencies."""
    experiment_path, main = get_main_file(globs, save_git_info)

    base_dir = base_dir or experiment_path

    gather_sources = source_discovery_strategies[SETTINGS["DISCOVER_SOURCES"]]
    sources = gather_sources(globs, base_dir, save_git_info)
    if main is not None:
        sources.add(main)

    gather_dependencies = dependency_discovery_strategies[
        SETTINGS["DISCOVER_DEPENDENCIES"]
    ]
    dependencies = gather_dependencies(globs, base_dir)

    if opt.has_numpy:
        # Add numpy as a dependency because it might be used for randomness
        dependencies.add(PackageDependency.create(opt.np))

    return main, sources, dependencies
