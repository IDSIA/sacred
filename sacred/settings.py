#!/usr/bin/env python
# coding=utf-8

import platform
from munch import munchify

__all__ = ("SETTINGS",)


SETTINGS = munchify(
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
            # regex patterns to filter out certain IDE or linter directives from
            # inline comments in the documentation
            "IGNORED_COMMENTS": ["^pylint:", "^noinspection"],
        },
        "HOST_INFO": {
            # Collect information about GPUs using the nvidia-smi tool
            "INCLUDE_GPU_INFO": True,
            # List of ENVIRONMENT variables to store in host-info
            "CAPTURED_ENV": [],
        },
        "COMMAND_LINE": {
            # disallow string fallback, if parsing a value from command-line failed
            "STRICT_PARSING": False,
            # show command line options that are disabled (e.g. unmet dependencies)
            "SHOW_DISABLED_OPTIONS": True,
        },
        # configure how stdout/stderr are captured. ['no', 'sys', 'fd']
        "CAPTURE_MODE": "sys" if platform.system() == "Windows" else "fd",
        # configure how dependencies are discovered. [none, imported, sys, pkg]
        "DISCOVER_DEPENDENCIES": "imported",
        # configure how source-files are discovered. [none, imported, sys, dir]
        "DISCOVER_SOURCES": "imported",
    }
)
