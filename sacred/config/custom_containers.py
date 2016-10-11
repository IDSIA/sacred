#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import sacred.optional as opt
from sacred.utils import join_paths

__sacred__ = True  # marks files that should be filtered from stack traces


class FallbackDict(dict):
    """Dictionary that defaults to a fallback dict for missing keys."""

    def __init__(self, fallback, **kwargs):
        super(FallbackDict, self).__init__(**kwargs)
        self.fallback = fallback

    def __getitem__(self, item):
        if dict.__contains__(self, item):
            return dict.__getitem__(self, item)
        else:
            return self.fallback[item]

    def __contains__(self, item):
        return dict.__contains__(self, item) or (item in self.fallback)

    def get(self, k, d=None):
        if dict.__contains__(self, k):
            return dict.__getitem__(self, k)
        else:
            return self.fallback.get(k, d)

    def items(self):
        raise NotImplementedError()

    def iteritems(self):
        raise NotImplementedError()

    def iterkeys(self):
        raise NotImplementedError()

    def itervalues(self):
        raise NotImplementedError()

    def keys(self):
        raise NotImplementedError()

    def pop(self, k, d=None):
        raise NotImplementedError()

    def popitem(self):
        raise NotImplementedError()

    def setdefault(self, k, d=None):
        raise NotImplementedError()

    def update(self, e=None, **f):
        raise NotImplementedError()

    def values(self):
        raise NotImplementedError()

    def viewitems(self):
        raise NotImplementedError()

    def viewkeys(self):
        raise NotImplementedError()

    def viewvalues(self):
        raise NotImplementedError()

    def __iter__(self):
        raise NotImplementedError()

    def __len__(self):
        raise NotImplementedError()


class DogmaticDict(dict):
    def __init__(self, fixed=None, fallback=None):
        super(DogmaticDict, self).__init__()
        self.typechanges = {}
        self.fallback_writes = []
        self.modified = set()
        self.fixed = fixed or {}
        self._fallback = {}
        if fallback:
            self.fallback = fallback

    @property
    def fallback(self):
        return self._fallback

    @fallback.setter
    def fallback(self, newval):
        ffkeys = set(self.fixed.keys()).intersection(set(newval.keys()))
        for k in ffkeys:
            if isinstance(self.fixed[k], DogmaticDict):
                self.fixed[k].fallback = newval[k]
            elif isinstance(self.fixed[k], dict):
                self.fixed[k] = DogmaticDict(self.fixed[k])
                self.fixed[k].fallback = newval[k]

        self._fallback = newval

    def _log_blocked_setitem(self, key, value, fixed_value):
        if type_changed(value, fixed_value):
            self.typechanges[key] = (type(value), type(fixed_value))

        if value != fixed_value:
            self.modified.add(key)

        # if both are dicts recursively collect modified and typechanges
        if isinstance(fixed_value, DogmaticDict) and isinstance(value, dict):
            for k, val in fixed_value.typechanges.items():
                self.typechanges[join_paths(key, k)] = val

            self.modified |= {join_paths(key, m) for m in fixed_value.modified}

    def __setitem__(self, key, value):
        if key not in self.fixed:
            if key in self.fallback:
                self.fallback_writes.append(key)
            return dict.__setitem__(self, key, value)

        fixed_value = self.fixed[key]
        dict.__setitem__(self, key, fixed_value)
        # if both are dicts do a recursive update
        if isinstance(fixed_value, DogmaticDict) and isinstance(value, dict):
            for k, val in value.items():
                fixed_value[k] = val

        self._log_blocked_setitem(key, value, fixed_value)

    def __getitem__(self, item):
        if dict.__contains__(self, item):
            return dict.__getitem__(self, item)
        elif item in self.fallback:
            if item in self.fixed:
                return self.fixed[item]
            else:
                return self.fallback[item]
        raise KeyError(item)

    def __contains__(self, item):
        return dict.__contains__(self, item) or (item in self.fallback)

    def get(self, k, d=None):
        if dict.__contains__(self, k):
            return dict.__getitem__(self, k)()
        else:
            return self.fallback.get(k, d)

    def has_key(self, item):
        return self.__contains__(item)

    def __delitem__(self, key):
        if key not in self.fixed:
            dict.__delitem__(self, key)

    def update(self, iterable=None, **kwargs):
        if iterable is not None:
            if hasattr(iterable, 'keys'):
                for key in iterable:
                    self[key] = iterable[key]
            else:
                for (key, value) in iterable:
                    self[key] = value
        for key in kwargs:
            self[key] = kwargs[key]

    def revelation(self):
        missing = set()
        for key in self.fixed:
            if not dict.__contains__(self, key):
                self[key] = self.fixed[key]
                missing.add(key)

            if isinstance(self[key], (DogmaticDict, DogmaticList)):
                missing |= {key + "." + k for k in self[key].revelation()}
        return missing


class DogmaticList(list):
    def append(self, p_object):
        pass

    def extend(self, iterable):
        pass

    def insert(self, index, p_object):
        pass

    def reverse(self):
        pass

    def sort(self, compare=None, key=None, reverse=False):
        pass

    def __iadd__(self, other):
        return self

    def __imul__(self, other):
        return self

    def __setitem__(self, key, value):
        pass

    def __setslice__(self, i, j, sequence):
        pass

    def __delitem__(self, key):
        pass

    def __delslice__(self, i, j):
        pass

    def pop(self, index=None):
        raise TypeError('Cannot pop from DogmaticList')

    def remove(self, value):
        pass

    def revelation(self):
        for obj in self:
            if isinstance(obj, (DogmaticDict, DogmaticList)):
                obj.revelation()
        return set()


SIMPLIFY_TYPE = {
    type(None): type(None),
    bool: bool,
    float: float,
    int: int,
    str: str,
    list: list,
    tuple: list,
    dict: dict,
    DogmaticDict: dict,
    DogmaticList: list,
}

# if in python 2 we want to ignore unicode/str and int/long typechanges
try:
    SIMPLIFY_TYPE[unicode] = str
    SIMPLIFY_TYPE[long] = int
except NameError:
    pass

# if numpy is available we also want to ignore typechanges from numpy
# datatypes to the corresponding python datatype
if opt.has_numpy:
    from sacred.optional import np
    NP_FLOATS = ['float', 'float16', 'float32', 'float64', 'float128']
    for npf in NP_FLOATS:
        if hasattr(np, npf):
            SIMPLIFY_TYPE[getattr(np, npf)] = float

    NP_INTS = ['int', 'int8', 'int16', 'int32', 'int64',
               'uint', 'uint8', 'uint16', 'uint32', 'uint64']
    for npi in NP_INTS:
        if hasattr(np, npi):
            SIMPLIFY_TYPE[getattr(np, npi)] = int

    SIMPLIFY_TYPE[np.bool_] = bool


def type_changed(old_value, new_value):
    sot = SIMPLIFY_TYPE.get(type(old_value), type(old_value))
    snt = SIMPLIFY_TYPE.get(type(new_value), type(new_value))
    return sot != snt and old_value is not None  # ignore typechanges from None
