#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from contextlib import contextmanager
import jsonpickle.tags

from sacred import SETTINGS
import sacred.optional as opt
from sacred.config.custom_containers import DogmaticDict, DogmaticList
from sacred.utils import PYTHON_IDENTIFIER
from sacred.optional import basestring


def assert_is_valid_key(key):
    """
    Raise KeyError if a given config key violates any requirements.

    The requirements are the following and can be individually deactivated
    in ``sacred.SETTINGS.CONFIG_KEYS``:
      * ENFORCE_MONGO_COMPATIBLE (default: True):
        make sure the keys don't contain a '.' or start with a '$'
      * ENFORCE_JSONPICKLE_COMPATIBLE (default: True):
        make sure the keys do not contain any reserved jsonpickle tags
        This is very important. Only deactivate if you know what you are doing.
      * ENFORCE_STRING (default: False):
        make sure all keys are string.
      * ENFORCE_VALID_PYTHON_IDENTIFIER (default: False):
        make sure all keys are valid python identifiers.

    Parameters
    ----------
    key:
      The key that should be checked

    Raises
    ------
    KeyError:
      if the key violates any requirements
    """
    if SETTINGS.CONFIG.ENFORCE_KEYS_MONGO_COMPATIBLE and (
            isinstance(key, basestring) and (key.find('.') > -1 or
                                             key.startswith('$'))):
        raise KeyError('Invalid key "{}". Config-keys cannot '
                       'contain "." or start with "$"'.format(key))

    if SETTINGS.CONFIG.ENFORCE_KEYS_JSONPICKLE_COMPATIBLE and \
            isinstance(key, basestring) and (
            key in jsonpickle.tags.RESERVED or key.startswith('json://')):
        raise KeyError('Invalid key "{}". Config-keys cannot be one of the'
                       'reserved jsonpickle tags: {}'
                       .format(key, jsonpickle.tags.RESERVED))

    if SETTINGS.CONFIG.ENFORCE_STRING_KEYS and (
            not isinstance(key, basestring)):
        raise KeyError('Invalid key "{}". Config-keys have to be strings, '
                       'but was {}'.format(key, type(key)))

    if SETTINGS.CONFIG.ENFORCE_VALID_PYTHON_IDENTIFIER_KEYS and (
            isinstance(key, basestring) and not PYTHON_IDENTIFIER.match(key)):
        raise KeyError('Key "{}" is not a valid python identifier'
                       .format(key))

    if SETTINGS.CONFIG.ENFORCE_KEYS_NO_EQUALS and (
            isinstance(key, basestring) and '=' in key):
        raise KeyError('Invalid key "{}". Config keys may not contain an'
                       'equals sign ("=").'.format('='))


def normalize_numpy(obj):
    if opt.has_numpy and isinstance(obj, opt.np.generic):
        try:
            return opt.np.asscalar(obj)
        except ValueError:
            pass
    return obj


def normalize_or_die(obj):
    if isinstance(obj, dict):
        res = dict()
        for key, value in obj.items():
            assert_is_valid_key(key)
            res[key] = normalize_or_die(value)
        return res
    elif isinstance(obj, (list, tuple)):
        return list([normalize_or_die(value) for value in obj])
    return normalize_numpy(obj)


def recursive_fill_in(config, preset):
    for key in preset:
        if key not in config:
            config[key] = preset[key]
        elif isinstance(config[key], dict):
            recursive_fill_in(config[key], preset[key])


def chain_evaluate_config_scopes(config_scopes, fixed=None, preset=None,
                                 fallback=None):
    fixed = fixed or {}
    fallback = fallback or {}
    final_config = dict(preset or {})
    config_summaries = []
    for config in config_scopes:
        cfg = config(fixed=fixed,
                     preset=final_config,
                     fallback=fallback)
        config_summaries.append(cfg)
        final_config.update(cfg)

    if not config_scopes:
        final_config.update(fixed)

    return undogmatize(final_config), config_summaries


def dogmatize(obj):
    if isinstance(obj, dict):
        return DogmaticDict({key: dogmatize(val) for key, val in obj.items()})
    elif isinstance(obj, list):
        return DogmaticList([dogmatize(value) for value in obj])
    elif isinstance(obj, tuple):
        return tuple(dogmatize(value) for value in obj)
    else:
        return obj


def undogmatize(obj):
    if isinstance(obj, DogmaticDict):
        return dict({key: undogmatize(value) for key, value in obj.items()})
    elif isinstance(obj, DogmaticList):
        return list([undogmatize(value) for value in obj])
    elif isinstance(obj, tuple):
        return tuple(undogmatize(value) for value in obj)
    else:
        return obj


class NameSpace(dict):
    def __init__(self, dogdict):
        super().__init__()
        self.dogdict = dogdict
        self._prefixes = []
        self.history = []

    def __setitem__(self, key, value):
        curr = self.dogdict
        for p in self._prefixes:
            curr = curr[p]
        curr[key] = value

    def __getitem__(self, item):
        potential_matches = []
        curr = self.dogdict
        for p in self._prefixes:
            if item in curr:
                potential_matches.append(curr[item])
            curr = curr[p]
        if potential_matches:
            return curr.get(item, potential_matches[-1])
        else:
            return curr[item]

    def get(self, k, default=None):
        try:
            return self[k]
        except KeyError:
            return default

    def __contains__(self, item):
        try:
            _ = self[item]
            return True
        except KeyError:
            return False

    def __delitem__(self, key):
        curr = self.dogdict
        for p in self._prefixes:
            curr = curr[p]
        del curr[key]

    def push_prefix(self, prefix, start, stop):
        self[prefix] = {}
        self._prefixes.append(prefix)
        self.history.append((start, stop, prefix))

    def pop_prefix(self):
        self._prefixes.pop()


@contextmanager
def enter_namespace(namespace, name, start, stop=None):
    namespace.push_prefix(name, start, stop)
    yield
    namespace.pop_prefix()
