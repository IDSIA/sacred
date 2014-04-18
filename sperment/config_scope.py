#!/usr/bin/python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from copy import copy
from functools import update_wrapper
import inspect
import json
import re


def blocking_dictify(x):
    if isinstance(x, dict):
        return BlockingDict({k: blocking_dictify(v) for k, v in x.iteritems()})
    elif isinstance(x, (list, tuple)):
        return type(x)(blocking_dictify(v) for v in x)
    else:
        return x


class BlockingDict(dict):
    def __init__(self, fixed=None):
        super(BlockingDict, self).__init__()
        if fixed is not None:
            self.update(fixed)
            self._fixed = fixed
        else:
            self._fixed = ()

    def __setitem__(self, key, value):
        if key not in self._fixed:
            super(BlockingDict, self).__setitem__(key, value)
        elif isinstance(self[key], BlockingDict) and isinstance(value, dict):
            #recursive update
            bd = self[key]
            for k, v in value.items():
                bd[k] = v


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
        assert is_zero_argument_function(func)
        self._func = func
        update_wrapper(self, func)
        func_body = get_function_body_source(func)
        self._body_code = compile(func_body, "<string>", "exec")

    def __call__(self, fixed=None, preset=None):
        self.clear()
        l = blocking_dictify(fixed) if fixed is not None else {}
        if preset is not None:
            l.update(preset)
        eval(self._body_code, copy(self._func.func_globals), l)
        for k, v in l.items():
            if k.startswith('_'):
                continue
            try:
                json.dumps(v)
                self[k] = v
            except TypeError:
                pass

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
