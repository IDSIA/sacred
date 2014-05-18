#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from copy import copy
from functools import update_wrapper
import inspect
import json
import re


def dogmatize(x):
    if isinstance(x, dict):
        return DogmaticDict({k: dogmatize(v) for k, v in x.items()})
    elif isinstance(x, list):
        return DogmaticList([dogmatize(v) for v in x])
    elif isinstance(x, tuple):
        return tuple(dogmatize(v) for v in x)
    else:
        return x


class DogmaticDict(dict):
    def __init__(self, fixed=None):
        super(DogmaticDict, self).__init__()
        if fixed is not None:
            self._fixed = fixed
        else:
            self._fixed = ()

    def __setitem__(self, key, value):
        if key not in self._fixed:
            dict.__setitem__(self, key, value)
        else:
            fixed_val = self._fixed[key]
            dict.__setitem__(self, key, fixed_val)
            if isinstance(fixed_val, DogmaticDict) and isinstance(value, dict):
                #recursive update
                bd = self[key]
                for k, v in value.items():
                    bd[k] = v

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
            if not key in self:
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

    def sort(self, cmp=None, key=None, reverse=False):
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


def is_zero_argument_function(func):
    arg_spec = inspect.getargspec(func)
    return (arg_spec.args == [] and
            arg_spec.varargs is None and
            arg_spec.keywords is None)


def get_function_body_source(func):
    func_code_lines, start_idx = inspect.getsourcelines(func)
    func_code = ''.join(func_code_lines)
    func_def = re.compile(
        r"^[ \t]*def[ \t]*{}[ \t]*\(\s*\)[ \t]*:[ \t]*\n".format(func.__name__),
        flags=re.MULTILINE)
    defs = list(re.finditer(func_def, func_code))
    assert defs
    func_body = func_code[defs[0].end():]
    return inspect.cleandoc(func_body)


class ConfigScope(dict):
    def __init__(self, func):
        super(ConfigScope, self).__init__()
        assert is_zero_argument_function(func), \
            "only zero-argument function can be ConfigScopes"
        self._func = func
        update_wrapper(self, func)
        func_body = get_function_body_source(func)
        self._body_code = compile(func_body, "<string>", "exec")
        self._initialized = False
        self.added_values = set()

    def __call__(self, fixed=None, preset=None):
        self._initialized = True
        self.clear()
        cfg_locals = dogmatize(fixed or {})
        if preset is not None:
            cfg_locals.update(preset)
        eval(self._body_code, copy(self._func.__globals__), cfg_locals)
        self.added_values = cfg_locals.revelation()

        for k, v in cfg_locals.items():
            if k.startswith('_'):
                continue
            try:
                json.dumps(v)
                self[k] = v
            except TypeError:
                pass
        return self

    def __getattr__(self, k):
        """
        Gets key if it exists, otherwise throws AttributeError.
        """
        try:
            # Throws exception if not in prototype chain
            return object.__getattribute__(self, k)
        except AttributeError:
            try:
                return self[k]
            except KeyError:
                raise AttributeError(k)

    def __getitem__(self, item):
        assert self._initialized, "ConfigScope has to be executed before access"
        return dict.__getitem__(self, item)