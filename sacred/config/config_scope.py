#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import ast
import inspect
import re
from copy import copy

from sacred.config.config_summary import ConfigSummary
from sacred.config.utils import dogmatize, normalize_or_die, recursive_fill_in

__sacred__ = True


class ConfigScope(object):
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
        self._body_code = get_function_body_code(func)

    def __call__(self, fixed=None, preset=None, fallback=None):
        """
        Evaluate this ConfigScope.

        This will evaluate the function body and fill the relevant local
        variables into entries into keys in this dictionary.

        :param fixed: Dictionary of entries that should stay fixed during the
                      evaluation. All of them will be part of the final config.
        :type fixed: dict
        :param preset: Dictionary of preset values that will be available
                       during the evaluation (if they are declared in the
                       function argument list). All of them will be part of the
                       final config.
        :type preset: dict
        :param fallback: Dictionary of fallback values that will be available
                         during the evaluation (if they are declared in the
                         function argument list). They will NOT be part of the
                         final config.
        :type fallback: dict
        :return: self
        :rtype: ConfigScope
        """
        cfg_locals = dogmatize(fixed or {})
        fallback = fallback or {}
        preset = preset or {}
        fallback_view = {}

        available_entries = set(preset.keys()) | set(fallback.keys())

        for arg in self.arg_spec.args:
            if arg not in available_entries:
                raise KeyError("'%s' not in preset for ConfigScope. "
                               "Available options are: %s" %
                               (arg, available_entries))
            if arg in preset:
                cfg_locals[arg] = preset[arg]
            else:  # arg in fallback
                fallback_view[arg] = fallback[arg]

        cfg_locals.fallback = fallback_view
        eval(self._body_code, copy(self._func.__globals__), cfg_locals)

        added = cfg_locals.revelation()
        config_summary = ConfigSummary(added, cfg_locals.modified,
                                       cfg_locals.typechanges,
                                       cfg_locals.ignored_fallback_writes)
        # fill in the unused presets
        recursive_fill_in(cfg_locals, preset)

        for key, value in cfg_locals.items():
            try:
                config_summary[key] = normalize_or_die(value)
            except ValueError:
                pass
        return config_summary


def get_function_body(func):
    func_code_lines, start_idx = inspect.getsourcelines(func)
    func_code = ''.join(func_code_lines)
    arg = "(?:[a-zA-Z_][a-zA-Z0-9_]*)"
    arguments = r"{0}(?:\s*,\s*{0})*".format(arg)
    func_def = re.compile(
        r"^[ \t]*def[ \t]*{}[ \t]*\(\s*({})?\s*\)[ \t]*:[ \t]*\n".format(
            func.__name__, arguments), flags=re.MULTILINE)
    defs = list(re.finditer(func_def, func_code))
    assert defs
    line_offset = start_idx + func_code[:defs[0].end()].count('\n') - 1
    func_body = func_code[defs[0].end():]
    return func_body, line_offset


def is_empty_or_comment(line):
    sline = line.strip()
    return sline == '' or sline.startswith('#')


def dedent_line(line, indent):
    for i, (line_sym, indent_sym) in enumerate(zip(line, indent)):
        if line_sym != indent_sym:
            start = i
            break
    else:
        start = len(indent)
    return line[start:]


def dedent_function_body(body):
    lines = body.split('\n')
    # find indentation by first line
    indent = ''
    for line in lines:
        if is_empty_or_comment(line):
            continue
        else:
            indent = re.match('^\s*', line).group()
            break

    out_lines = [dedent_line(line, indent) for line in lines]
    return '\n'.join(out_lines)


def get_function_body_code(func):
    filename = inspect.getfile(func)
    func_body, line_offset = get_function_body(func)
    body_source = dedent_function_body(func_body)
    body_code = compile(body_source, filename, "exec", ast.PyCF_ONLY_AST)
    body_code = ast.increment_lineno(body_code, n=line_offset)
    body_code = compile(body_code, filename, "exec")
    return body_code
