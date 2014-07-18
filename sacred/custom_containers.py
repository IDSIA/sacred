#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from sacred.utils import join_paths


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
        raise NotImplemented

    def iteritems(self):
        raise NotImplemented

    def iterkeys(self):
        raise NotImplemented

    def itervalues(self):
        raise NotImplemented

    def keys(self):
        raise NotImplemented

    def pop(self, k, d=None):
        raise NotImplemented

    def popitem(self):
        raise NotImplemented

    def setdefault(self, k, d=None):
        raise NotImplemented

    def update(self, E=None, **F):
        raise NotImplemented

    def values(self):
        raise NotImplemented

    def viewitems(self):
        raise NotImplemented

    def viewkeys(self):
        raise NotImplemented

    def viewvalues(self):
        raise NotImplemented

    def __iter__(self):
        raise NotImplemented

    def __len__(self):
        raise NotImplemented


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
                #recursive update
                bd = self[key]
                for k, v in value.items():
                    bd[k] = v

                for k, v in bd.typechanges.items():
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

            if isinstance(self[key], DogmaticDict):
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


def type_changed(a, b):
    if isinstance(a, DogmaticDict) or isinstance(b, DogmaticDict):
        return not (isinstance(a, dict) and isinstance(b, dict))
    if isinstance(a, DogmaticList) or isinstance(b, DogmaticList):
        return not (isinstance(a, list) and isinstance(b, list))
    return type(a) != type(b)


def dogmatize(x, with_fallback=()):
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