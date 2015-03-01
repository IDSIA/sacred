#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import json

import sacred.optional as opt
import six
from sacred.config.custom_containers import DogmaticDict, DogmaticList


def assert_is_valid_key(key):
    if not isinstance(key, six.string_types):
        raise KeyError('Invalid key "{}". Config-keys have to be strings, '
                       'but was {}'.format(key, type(key)))
    elif key.find('.') > -1 or key.find('$') > -1:
        raise KeyError('Invalid key "{}". Config-keys cannot '
                       'contain "." or "$"'.format(key))


def normalize_or_die(obj):
    if isinstance(obj, dict):
        res = dict()
        for key, value in obj.items():
            assert_is_valid_key(key)
            res[key] = normalize_or_die(value)
        return res
    elif isinstance(obj, (list, tuple)):
        return list([normalize_or_die(value) for value in obj])
    elif opt.has_numpy and isinstance(obj, opt.np.bool_):
        # fixes an issue with numpy.bool_ not being json-serializable
        return bool(obj)
    else:
        try:
            json.dumps(obj)
            return obj
        except TypeError:
            raise ValueError("Invalid value '{}'. All values have to be"
                             "JSON-serializeable".format(obj))


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
