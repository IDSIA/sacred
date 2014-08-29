#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import ast
from copy import copy
from functools import update_wrapper
import inspect
import json
import re

from sacred.custom_containers import dogmatize, undogmatize


__sacred__ = True


def get_function_body_code(func):
    func_code_lines, start_idx = inspect.getsourcelines(func)
    filename = inspect.getfile(func)
    func_code = ''.join(func_code_lines)
    arg = "(?:[a-zA-Z_][a-zA-Z0-9_]*)"
    arguments = r"{0}(?:\s*,\s*{0})*".format(arg)
    func_def = re.compile(
        r"^[ \t]*def[ \t]*{}[ \t]*\(\s*({})?\s*\)[ \t]*:[ \t]*\n\s*".format(
            func.__name__, arguments), flags=re.MULTILINE)
    defs = list(re.finditer(func_def, func_code))
    assert defs
    line_offset = func_code[:defs[0].end()].count('\n')
    func_body = func_code[defs[0].end():]
    body_code = compile(inspect.cleandoc(func_body), filename, "exec",
                        ast.PyCF_ONLY_AST)
    body_code = ast.increment_lineno(body_code, n=start_idx+line_offset-1)
    body_code = compile(body_code, filename, "exec")
    return body_code


class ConfigScope(dict):
    def __init__(self, func):
        super(ConfigScope, self).__init__()
        self.arg_spec = inspect.getargspec(func)
        assert self.arg_spec.varargs is None, \
            "varargs are not allowed for ConfigScope functions"
        assert self.arg_spec.keywords is None, \
            "kwargs are not allowed for ConfigScope functions"
        assert self.arg_spec.defaults is None, \
            "default values are not allowed for ConfigScope functions"

        self._func = func
        update_wrapper(self, func)
        self._body_code = get_function_body_code(func)
        self._initialized = False
        self.added_values = set()
        self.typechanges = {}

    def __call__(self, fixed=None, preset=None, fallback=None):
        self._initialized = True
        self.clear()
        cfg_locals = dogmatize(fixed or {})
        fallback = fallback or {}
        if preset is None:
            assert self.arg_spec.args == [], \
                "'%s' not in preset for ConfigScope. (There are no presets)"
        else:
            for a in self.arg_spec.args:
                assert a in preset or a in fallback, \
                    "'%s' not in preset for ConfigScope. " \
                    "Available options are: %s" % (a, preset.keys())
                if a in preset:
                    cfg_locals[a] = preset[a]
                else:
                    assert a in fallback, "'%s' not in preset for ConfigScope."\
                                          " Available options are: %s" % \
                                          (a, preset.keys() + fallback.keys())

        cfg_locals.fallback = fallback
        eval(self._body_code, copy(self._func.__globals__), cfg_locals)
        self.added_values = cfg_locals.revelation()
        self.typechanges = cfg_locals.typechanges
        for k, v in cfg_locals.items():
            if k.startswith('_'):
                continue
            try:
                json.dumps(v)
                self[k] = undogmatize(v)
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