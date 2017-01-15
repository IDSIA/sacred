#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from munch import munchify

__sacred__ = True  # marks files that should be filtered from stack traces

__all__ = ('SETTINGS', )


SETTINGS = munchify({
    'CONFIG_KEYS': {
        # make sure all config keys are compatible with MongoDB
        'ENFORCE_MONGO_COMPATIBLE': True,
        # make sure all config keys are serializable with jsonpickle
        # THIS IS IMPORTANT. Only deactivate if you know what you're doing.
        'ENFORCE_JSONPICKLE_COMPATIBLE': True,
        # make sure all config keys are valid python identifiers
        'ENFORCE_VALID_PYTHON_IDENTIFIER': False,
        # make sure all config keys are strings
        'ENFORCE_STRING': False,
        # make sure no config key contains an equals sign
        'ENFORCE_NO_EQUALS': True
    },
    # regex patterns to filter out certain IDE or linter directives from
    # inline comments in the documentation
    'IGNORED_CONFIG_COMMENTS': ['^pylint:', '^noinspection']
})
