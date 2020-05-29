#!/usr/bin/env python
# coding=utf-8
import copy

import sacred.optional as opt
from sacred.utils import join_paths, SacredError


def fallback_dict(fallback, **kwargs):
    fallback_copy = fallback.copy()
    fallback_copy.update(kwargs)
    return fallback_copy


class DogmaticDict(dict):
    def __init__(self, fixed=None, fallback=None):
        super().__init__()
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

        if is_different(value, fixed_value):
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
            return dict.__getitem__(self, k)
        else:
            return self.fallback.get(k, d)

    def has_key(self, item):
        return self.__contains__(item)

    def __delitem__(self, key):
        if key not in self.fixed:
            dict.__delitem__(self, key)

    def update(self, iterable=None, **kwargs):
        if iterable is not None:
            if hasattr(iterable, "keys"):
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
        raise TypeError("Cannot pop from DogmaticList")

    def remove(self, value):
        pass

    def revelation(self):
        for obj in self:
            if isinstance(obj, (DogmaticDict, DogmaticList)):
                obj.revelation()
        return set()


def _passthrough(fn):
    def f(self, *args, **kwargs):
        return fn(self.container, *args, **kwargs)

    return f


DEFAULT_READONLY_MSG = "This container is read-only"


class ReadOnlyDict(dict):
    """
    A read-only variant of a `dict`.
    """

    def __init__(self, container, message=DEFAULT_READONLY_MSG):
        # Call list init
        self.container = dict(container)
        # NOTE: You need to make a dict.__init__(self, x) call in order
        # to get Python's C implementation of JSON to encode dict(x).
        # Without this super call, JSON always encodes this object as "{}".
        dict.__init__(self, dict(container))
        # collections.abc.Mapping.__init__(self)
        self.message = message

    def _readonly(self, *args, **kwargs):
        raise SacredError(self.message, filter_traceback="always")

    # Disallow mutating functions.
    __delitem__ = _readonly
    __setitem__ = _readonly
    clear = _readonly
    pop = _readonly
    popitem = _readonly
    setdefault = _readonly
    update = _readonly

    # Pass through read-only functions.
    __contains__ = _passthrough(dict.__contains__)
    __getitem__ = _passthrough(dict.__getitem__)
    __iter__ = _passthrough(dict.__iter__)
    __len__ = _passthrough(dict.__len__)
    __repr__ = _passthrough(dict.__repr__)
    __str__ = _passthrough(dict.__str__)
    copy = _passthrough(dict.copy)
    get = _passthrough(dict.get)
    keys = _passthrough(dict.keys)
    values = _passthrough(dict.values)
    items = _passthrough(dict.items)

    def __copy__(self):
        return dict(self.container)

    def __deepcopy__(self, memo):
        d = dict(self.container)
        return copy.deepcopy(d, memo=memo)

    def __reduce__(self):
        return ReadOnlyDict, (self.container, self.message)


class ReadOnlyList(list):
    """
    A read-only variant of a `list`.
    """

    def __init__(self, container, message=DEFAULT_READONLY_MSG):
        # list.__init__(self)
        # Call list init
        self.container = list(container)
        self.message = message

    def _readonly(self, *args, **kwargs):
        raise SacredError(self.message, filter_traceback="always")

    # Disallow mutating functions
    append = _readonly
    clear = _readonly
    extend = _readonly
    insert = _readonly
    pop = _readonly
    remove = _readonly
    reverse = _readonly
    sort = _readonly
    __setitem__ = _readonly
    __delitem__ = _readonly

    # Pass through read-only functions.
    __contains__ = _passthrough(list.__contains__)
    __getitem__ = _passthrough(list.__getitem__)
    __iter__ = _passthrough(list.__iter__)
    __len__ = _passthrough(list.__len__)
    __repr__ = _passthrough(list.__repr__)
    __reversed__ = _passthrough(list.__reversed__)
    __str__ = _passthrough(list.__str__)
    index = _passthrough(list.index)
    count = _passthrough(list.count)

    def __copy__(self):
        return [*self.container]

    def __eq__(self, other):
        # Passthrough list fails when comparing `self == self`, among
        # other things.
        if not isinstance(other, list):
            return False
        if len(self) != len(other):
            return False
        for x, y in zip(self, other):
            if x != y:
                return False
        return True

    def __ne__(self, other):
        # `self != self` goes to list.__ne__ without this stub.
        return not self.__eq__(other)

    def __deepcopy__(self, memo):
        lst = list(self.container)
        return copy.deepcopy(lst, memo=memo)

    def __reduce__(self):
        return ReadOnlyList, (self.container, self.message)


def make_read_only(o, error_message=DEFAULT_READONLY_MSG):
    """
    Converts every `list` and `dict` into `ReadOnlyList` and `ReadOnlyDict` in
    a nested structure of `list`s, `dict`s and `tuple`s. Does not modify `o`
    but returns the converted structure.
    """
    if type(o) == dict:
        return ReadOnlyDict(
            {k: make_read_only(v, error_message) for k, v in o.items()},
            error_message,
        )
    elif type(o) == list:
        return ReadOnlyList(
            [make_read_only(v, error_message) for v in o],
            error_message,
        )
    elif type(o) == tuple:
        return tuple(make_read_only(v, error_message) for v in o)
    else:
        return o


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

# if numpy is available we also want to ignore typechanges from numpy
# datatypes to the corresponding python datatype
if opt.has_numpy:
    from sacred.optional import np

    NP_FLOATS = ["float", "float16", "float32", "float64", "float128"]
    for npf in NP_FLOATS:
        if hasattr(np, npf):
            SIMPLIFY_TYPE[getattr(np, npf)] = float

    NP_INTS = [
        "int",
        "int8",
        "int16",
        "int32",
        "int64",
        "uint",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
    ]
    for npi in NP_INTS:
        if hasattr(np, npi):
            SIMPLIFY_TYPE[getattr(np, npi)] = int

    SIMPLIFY_TYPE[np.bool_] = bool


def type_changed(old_value, new_value):
    sot = SIMPLIFY_TYPE.get(type(old_value), type(old_value))
    snt = SIMPLIFY_TYPE.get(type(new_value), type(new_value))
    return sot != snt and old_value is not None  # ignore typechanges from None


def is_different(old_value, new_value):
    """Numpy aware comparison between two values."""
    if opt.has_numpy:
        return not opt.np.array_equal(old_value, new_value)
    else:
        return old_value != new_value
