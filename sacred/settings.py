#!/usr/bin/env python
# coding=utf-8

import platform
from sacred.utils import SacredError
import sacred.optional as opt
from munch import Munch
from packaging import version

__all__ = ("SETTINGS", "SettingError")


class SettingError(SacredError):
    """Error for invalid settings."""


class FrozenKeyMunch(Munch):
    __frozen_keys = False

    def freeze_keys(self):
        if self.__frozen_keys:
            return
        self.__frozen_keys = True
        for v in self.values():
            if isinstance(v, FrozenKeyMunch):
                v.freeze_keys()

    def _check_can_set(self, key, value):
        if not self.__frozen_keys:
            return

        # Don't allow unknown keys
        if key not in self:
            raise SettingError(
                f"Unknown setting: {key}. Possible keys are: " f"{list(self.keys())}"
            )

        # Don't allow setting keys that represent nested settings
        if isinstance(self[key], Munch) and not isinstance(value, Munch):
            # We don't want to overwrite a munch mapping. This is the easiest
            # solution and closest to the original implementation where setting
            # a setting with a dict would likely at some point cause an
            # exception
            raise SettingError(
                f"Can't set this setting ({key}) to a non-munch value "
                f"{value}, it is a nested setting!"
            )

    def __setitem__(self, key, value):
        self._check_can_set(key, value)
        super().__setitem__(key, value)

    def __setattr__(self, key, value):
        self._check_can_set(key, value)
        super().__setattr__(key, value)

    def __deepcopy__(self, memodict=None):
        obj = self.__class__.fromDict(self.toDict())
        if self.__frozen_keys:
            obj.freeze_keys()
        return obj


SETTINGS = FrozenKeyMunch.fromDict(
    {
        "CONFIG": {
            # make sure all config keys are compatible with MongoDB
            "ENFORCE_KEYS_MONGO_COMPATIBLE": True,
            # make sure all config keys are serializable with jsonpickle
            # THIS IS IMPORTANT. Only deactivate if you know what you're doing.
            "ENFORCE_KEYS_JSONPICKLE_COMPATIBLE": True,
            # make sure all config keys are valid python identifiers
            "ENFORCE_VALID_PYTHON_IDENTIFIER_KEYS": False,
            # make sure all config keys are strings
            "ENFORCE_STRING_KEYS": False,
            # make sure no config key contains an equals sign
            "ENFORCE_KEYS_NO_EQUALS": True,
            # if true, all dicts and lists in the configuration of a captured
            # function are replaced with a read-only container that raises an
            # Exception if it is attempted to write to those containers
            "READ_ONLY_CONFIG": True,
            # regex patterns to filter out certain IDE or linter directives
            # from inline comments in the documentation
            "IGNORED_COMMENTS": ["^pylint:", "^noinspection"],
            # if true uses the numpy legacy API, i.e. _rnd in captured functions is
            # a numpy.random.RandomState rather than numpy.random.Generator.
            # numpy.random.RandomState became legacy with numpy v1.19.
            "NUMPY_RANDOM_LEGACY_API": version.parse(opt.np.__version__)
            < version.parse("1.19")
            if opt.has_numpy
            else False,
        },
        "HOST_INFO": {
            # Collect information about GPUs using the nvidia-smi tool
            "INCLUDE_GPU_INFO": True,
            # Collect information about CPUs using py-cpuinfo
            "INCLUDE_CPU_INFO": True,
            # List of ENVIRONMENT variables to store in host-info
            "CAPTURED_ENV": [],
        },
        "COMMAND_LINE": {
            # disallow string fallback, if parsing a value from command-line
            # failed
            "STRICT_PARSING": False,
            # show command line options that are disabled (e.g. unmet
            # dependencies)
            "SHOW_DISABLED_OPTIONS": True,
        },
        # configure how stdout/stderr are captured. ['no', 'sys', 'fd']
        "CAPTURE_MODE": "sys" if platform.system() == "Windows" else "fd",
        # configure how dependencies are discovered. [none, imported, sys, pkg]
        "DISCOVER_DEPENDENCIES": "imported",
        # configure how source-files are discovered. [none, imported, sys, dir]
        "DISCOVER_SOURCES": "imported",
        # Configure the default beat interval, in seconds
        "DEFAULT_BEAT_INTERVAL": 10.0,
    },
)
SETTINGS.freeze_keys()
