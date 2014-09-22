#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from sacred.utils import join_paths


__sacred__ = True  # marker for filtering stacktraces when run from commandline


class FallbackDict(dict):
    """
    This dictionary either returns the value assigned to a given key or it
    returns the value for that key from the fallback dict.
    """
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
            return dict.__getitem__(self, k)()
        else:
            return self.fallback.get(k, d)

    def has_key(self, item):
        return self.__contains__(item)

    def items(self):
        raise NotImplementedError

    def iteritems(self):
        raise NotImplementedError

    def iterkeys(self):
        raise NotImplementedError

    def itervalues(self):
        raise NotImplementedError

    def keys(self):
        raise NotImplementedError

    def pop(self, k, d=None):
        raise NotImplementedError

    def popitem(self):
        raise NotImplementedError

    def setdefault(self, k, d=None):
        raise NotImplementedError

    def update(self, e=None, **f):
        raise NotImplementedError

    def values(self):
        raise NotImplementedError

    def viewitems(self):
        raise NotImplementedError

    def viewkeys(self):
        raise NotImplementedError

    def viewvalues(self):
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError


class DogmaticDict(dict):
    def __init__(self, fixed=None, fallback=None):
        super(DogmaticDict, self).__init__()
        self.typechanges = {}
        self._fixed = fixed or {}
        self._fallback = {}
        if fallback:
            self.fallback = fallback

    @property
    def fallback(self):
        return self._fallback

    @fallback.setter
    def fallback(self, newval):
        ffkeys = set(self._fixed.keys()).intersection(set(newval.keys()))
        if ffkeys:
            raise ValueError("Keys %s appear are both fixed and fallback keys"
                             % ffkeys)
        self._fallback = newval

    def __setitem__(self, key, value):
        if key not in self._fixed:
            dict.__setitem__(self, key, value)
        else:
            fixed_val = self._fixed[key]
            dict.__setitem__(self, key, fixed_val)
            # log typechanges
            if type_changed(value, fixed_val):
                self.typechanges[key] = (type(value), type(fixed_val))

            if isinstance(fixed_val, DogmaticDict) and isinstance(value, dict):
                # recursive update
                for k, v in value.items():
                    fixed_val[k] = v

                for k, v in fixed_val.typechanges.items():
                    self.typechanges[join_paths(key, k)] = v

    def __getitem__(self, item):
        if dict.__contains__(self, item):
            return dict.__getitem__(self, item)
        elif item in self.fallback:
            if item in self._fixed:
                return self._fixed[item]
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
        if key not in self._fixed:
            dict.__delitem__(self, key)

    def update(self, iterable=None, **kwargs):
        if iterable is not None:
            if hasattr(iterable, 'keys'):
                for k in iterable:
                    self[k] = iterable[k]
            else:
                for (k, v) in iterable:
                    self[k] = v
        for k in kwargs:
            self[k] = kwargs[k]

    def revelation(self):
        missing = set()
        for key in self._fixed:
            if not dict.__contains__(self, key):
                self[key] = self._fixed[key]
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
        for x in self:
            if isinstance(x, (DogmaticDict, DogmaticList)):
                x.revelation()
        return set()


simplify_type = {
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
    simplify_type[unicode] = str
    simplify_type[long] = int
except NameError:
    pass

# if numpy is available we also want to ignore typechanges from numpy
# datatypes to the corresponding python datatype
try:
    import numpy as np
    np_floats = [np.float, np.float16, np.float32, np.float64, np.float128]
    for npf in np_floats:
        simplify_type[npf] = float

    np_ints = [np.int, np.int8, np.int16, np.int32, np.int64,
               np.uint8, np.uint16, np.uint32, np.uint64]
    for npi in np_ints:
        simplify_type[npi] = int

    simplify_type[np.bool_] = bool
except ImportError:
    pass


def type_changed(a, b):
    return simplify_type[type(a)] != simplify_type[type(b)]


def dogmatize(x):
    if isinstance(x, dict):
        return DogmaticDict({k: dogmatize(v) for k, v in x.items()})
    elif isinstance(x, list):
        return DogmaticList([dogmatize(v) for v in x])
    elif isinstance(x, tuple):
        return tuple(dogmatize(v) for v in x)
    else:
        return x


def undogmatize(x):
    if isinstance(x, DogmaticDict):
        return dict({k: undogmatize(v) for k, v in x.items()})
    elif isinstance(x, DogmaticList):
        return list([undogmatize(v) for v in x])
    elif isinstance(x, tuple):
        return tuple(undogmatize(v) for v in x)
    else:
        return x
