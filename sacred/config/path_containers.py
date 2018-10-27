#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import json
from copy import copy
from collections import Mapping, Iterable
from functools import partial

from sacred.config.path import Path


##############################################################################
#                               conversion                                   #
##############################################################################
from sacred.sentinels import NotSet


def recursive_path_conversion(value, _converters=None):
    if isinstance(value, (PathDict, PathList, PathTuple)):
        return value
    if isinstance(value, dict):
        return PathDict(value, _converters=_converters)
    elif isinstance(value, list):
        return PathList(value, _converters=_converters)
    elif isinstance(value, tuple):
        return PathTuple(value, _converters=_converters)
    else:
        return ConfigEntry(value)


def recursive_unconversion(value):
    if isinstance(value, (PathDict, dict)):
        return {k: recursive_unconversion(v) for k, v in dict.items(value)}
    elif isinstance(value, (PathTuple, tuple)):
        return tuple([recursive_unconversion(v) for v in value])
    elif isinstance(value, (PathList, list)):
        return list([recursive_unconversion(v) for v in value])
    else:
        return value.value


##############################################################################
#                                 ConfigEntry                                #
##############################################################################

class ConfigEntry(object):
    """Represents a config value along with some meta information."""
    def __init__(self, value=NotSet, doc=NotSet, fixed=False,
                 default=NotSet):
        self.value = value
        self.doc = doc
        self.fixed = fixed
        self.default = default

    def update(self, entry):
        if not self.fixed:
            self.value = self.value if entry.value == NotSet else entry.value
        self.fixed = self.fixed or entry.fixed
        self.doc = self.doc if entry.doc == NotSet else entry.doc
        self.default = self.default if entry.default == NotSet else entry.default

    def __str__(self):
        return "<ConfigEntry: {}, fixed={}, default={}>".format(self.value, self.fixed, self.default)


##############################################################################
#                                 Tuple                                      #
##############################################################################

class PathTuple(tuple):
    """Behaves like normal tuple, but handles Paths and auto-converts items"""

    @staticmethod
    def __new__(cls, seq=(), _converters=(recursive_path_conversion,)):
        def _convert_value(value):
            for convert in _converters:
                value = convert(value, _converters=_converters)
            return value

        # noinspection PyArgumentList
        return tuple.__new__(cls, [_convert_value(x) for x in seq])

    def __getitem__(self, key):
        if not isinstance(key, Path):
            return super().__getitem__(key)

        with key as (first, rest):
            entry = super().__getitem__(first)
            return entry[rest] if rest else entry

    def __contains__(self, key):
        if not isinstance(key, Path):
            return super().__contains__(key)

        with key as (first, rest):
            try:
                sub_item = self[first]
                return sub_item.__contains__(rest) if rest else True
            except (IndexError, AttributeError):
                return False


##############################################################################
#                                 List                                       #
##############################################################################

class PathList(list):
    """Behaves like normal list, but handles Paths and auto-converts items"""

    def __init__(self, iterable=(), _converters=(recursive_path_conversion,)):
        self._converters = _converters
        super().__init__([self._convert_value(x) for x in iterable])

    def __getitem__(self, key):
        if not isinstance(key, Path):
            return super().__getitem__(key)

        with key as (first, rest):
            entry = super().__getitem__(first)
            return entry[rest] if rest else entry

    def __setitem__(self, key, value):
        value = self._convert_value(value)

        if not isinstance(key, Path):
            return super().__setitem__(key, value)

        with key as (first, rest):
            if rest:
                return self[first].__setitem__(rest, value)
            else:
                return super().__setitem__(first, value)

    def __delitem__(self, key):
        if not isinstance(key, Path):
            return super().__delitem__(key)

        with key as (first, rest):
            if rest:
                return self[first].__delitem__(rest)
            else:
                return super().__delitem__(first)

    def __contains__(self, key):
        if not isinstance(key, Path):
            return super().__contains__(key)

        with key as (first, rest):
            try:
                sub_item = self[first]
                return sub_item.__contains__(rest) if rest else True
            except (IndexError, AttributeError):
                return False

    def append(self, obj):
        list.append(self, self._convert_value(obj))

    def extend(self, iterable):
        list.extend(self, self._convert_value(iterable))

    def _convert_value(self, value):
        for convert in self._converters:
            value = convert(value, _converters=self._converters)
        return value


##############################################################################
#                                 Dict                                       #
##############################################################################

class PathDict(dict):
    """ Subclass of dict that allows path and attribute access.
    It also internally holds ConfigEntries which store meta-information.

    Based on bunch/munch packages.
    """
    def __init__(self, seq=None, _converters=(recursive_path_conversion,), **kwargs):
        """
        AttributeDict() -> new empty AttributeDict
        AttributeDict(mapping) -> new dictionary initialized from a mapping
            object's (key, value) pairs
        AttributeDict(iterable) -> new dictionary initialized as if via:
            d = {}
            for k, v in iterable:
                d[k] = v
        AttributeDict(**kwargs) -> new dictionary initialized with the
            name=value pairs in the keyword argument list.
            For example:  dict(one=1, two=2)
        """
        super().__init__()
        object.__setattr__(self, '_converters', _converters)
        self.update(seq, **kwargs)

    def __getattr__(self, key):
        try:
            # Throws exception if not in prototype chain
            return object.__getattribute__(self, key)
        except AttributeError:
            try:
                return self[key]
            except KeyError:
                raise AttributeError(key)

    def __setattr__(self, key, value):
        try:
            # Throws exception if not in prototype chain
            object.__getattribute__(self, key)
        except AttributeError:
            try:
                self[key] = value
            except KeyError:
                raise AttributeError(key)
        else:
            object.__setattr__(self, key, value)

    def __delattr__(self, key):
        try:
            # Throws exception if not in prototype chain
            object.__getattribute__(self, key)
        except AttributeError:
            try:
                del self[key]
            except KeyError:
                raise AttributeError(key)
        else:
            object.__delattr__(self, key)

    def get_entry(self, key):
        if not isinstance(key, Path):
            return super().__getitem__(key)
        with key as (first, rest):
            entry = super().__getitem__(first)
            return entry[rest] if rest else entry

    def __getitem__(self, key):
        entry = self.get_entry(key)
        return entry

    def __delitem__(self, key):
        # ignore deletion if corresponding entry is fixed
        entry = self.get_entry(key)
        if entry.fixed:
            return

        if not isinstance(key, Path):
            return super().__delitem__(key)

        with key as (first, rest):
            if rest:
                return self[first].__delitem__(rest)
            else:
                return super().__delitem__(first)

    def __setitem__(self, key, value, default=None):
        # TODO do we need to handle default?
        entry = self._convert_value(value)
        self.update_entry(key, entry, default)

    def update_entry(self, key, entry, default=None):
        if key in self:
            old_entry = self.get_entry(key)
            old_entry.update(entry)
            return

        if not isinstance(key, Path):
            super().__setitem__(key, entry)
            return

        with key as (first, rest):
            if rest:
                if default is None:
                    to_update = self[first]
                else:
                    to_update = self.setdefault(first, default())
                to_update[rest].update_entry(entry)
            else:
                super().__setitem__(first, entry)

    def __contains__(self, key):
        if not isinstance(key, Path):
            return super().__contains__(key)

        with key as (first, rest):
            if rest:
                return super().__contains__(first) and self[first].__contains__(rest)
            else:
                return super().__contains__(first)

    def update(self, m=None, **kwargs):
        items = []
        if isinstance(m, Mapping):
            items.extend(m.items())
        elif isinstance(m, Iterable):
            items.extend(m)
        elif m is not None:
            raise ValueError('Invalid m: has to be mapping or iterable, but was {}'.format(type(m)))

        if kwargs:
            items.extend(kwargs.items())

        default = partial(PathDict, _converters=self._converters)
        for k, v in items:
            self.__setitem__(k, v, default)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.to_dict())

    # @property
    # def __dict__(self):
    #     return {k: v for k, v in self.items() if isinstance(k, str)}

    def copy(self):
        return copy(self)

    def _convert_value(self, value):
        for convert in self._converters:
            value = convert(value, _converters=self._converters)
        return value

    def to_dict(self):
        return recursive_unconversion(self)

    def recursive_update(self, d=None, **kwargs):
        """
        Given a dictionaries d, update dict d recursively.

        E.g.:
        d = {'a': {'b' : 1}}
        u = {'c': 2, 'a': {'d': 3}}
        => {'a': {'b': 1, 'd': 3}, 'c': 2}
        """
        assert d or kwargs
        d = self._convert_value(kwargs if d is None else d)
        for k, v in d.flat_items():
            self.__setitem__(k, v, PathDict)

    def __enter__(self):
        """To support
        with cfg/"network"/"layer" as net:
            net.size=10
            net.act="tanh"
        """
        return self

    def __exit__(self, *args, **kwargs):
        return

    def __truediv__(self, other):
        return self.setdefault(other, self.__class__())

    def flat_items(self):
        yield from iterate_flattened(self)

    def to_json(self):
        return json.dumps(self.to_dict(), sort_keys=True)

    def items(self):
        return self.to_dict().items()

    def values(self):
        return self.to_dict().values()


##############################################################################
#                                 Utils                                      #
##############################################################################


def _by_str_key(x):
    k, v = x
    return str(k)


def _non_dicts_first(x):
    k, v = x
    return isinstance(v, dict), str(k)


def iterate_flattened(d, key=Path(), key_func=_by_str_key):
    """
    Recursively iterate over the entries of nested dicts, lists, and tuples.

    Provides a full Path for each leaf.
    """
    if isinstance(d, Mapping):
        for k, value in sorted(d.items(), key=key_func):
            yield from iterate_flattened(value, key + Path(k), key_func=key_func)
    elif isinstance(d, (list, tuple)):
        for i, value in enumerate(d):
            yield from iterate_flattened(value, key + Path(i), key_func=key_func)
    else:
        yield key, d