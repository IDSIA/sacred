#!/usr/bin/python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from copy import copy
import inspect
import json


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


class ConfigScope(dict):
    def __init__(self, func):
        super(ConfigScope, self).__init__()
        self._func = func
        arg_spec = inspect.getargspec(func)
        assert arg_spec.args == []
        assert arg_spec.varargs is None
        assert arg_spec.keywords is None

        func_code = inspect.getsourcelines(func)[0]
        assert func_code[0].strip().startswith('@')
        assert func_code[1].strip().startswith('def ')
        assert func_code[1].strip().endswith(':')
        #TODO: do more sophisticated body extraction than just skipping 2 lines
        body = inspect.cleandoc(''.join(func_code[2:]))
        self._body_code = compile(body, "<string>", "exec")
        self.execute()

    def execute(self, fixed=None):
        self.clear()
        l = blocking_dictify(fixed) if fixed is not None else {}
        eval(self._body_code, copy(self._func.func_globals), l)
        for k, v in l.items():
            if k.startswith('_'):
                continue
            if hasattr(v, '__nested_func__'):
                print('nested:', v)
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
