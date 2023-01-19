#!/usr/bin/env python
# coding=utf-8

import ast
import inspect
import io
import re
import textwrap
import token

from copy import copy
from sacred import SETTINGS
from sacred.config.config_summary import ConfigSummary
from sacred.config.utils import dogmatize, normalize_or_die, recursive_fill_in
from sacred.config.signature import get_argspec
from sacred.utils import ConfigError
from tokenize import generate_tokens, tokenize, TokenError, COMMENT


class ConfigScope:
    def __init__(self, func):
        self.args, vararg_name, kw_wildcard, _, kwargs = get_argspec(func)
        assert vararg_name is None, "*args not allowed for ConfigScope functions"
        assert kw_wildcard is None, "**kwargs not allowed for ConfigScope functions"
        assert not kwargs, "default values are not allowed for ConfigScope functions"

        self._func = func
        self._body_code = get_function_body_code(func)
        self._var_docs = get_config_comments(func)
        self.__doc__ = self._func.__doc__

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

        for arg in self.args:
            if arg not in available_entries:
                raise KeyError(
                    "'{}' not in preset for ConfigScope. "
                    "Available options are: {}".format(arg, available_entries)
                )
            if arg in preset:
                cfg_locals[arg] = preset[arg]
            else:  # arg in fallback
                fallback_view[arg] = fallback[arg]

        cfg_locals.fallback = fallback_view

        with ConfigError.track(cfg_locals):
            eval(self._body_code, copy(self._func.__globals__), cfg_locals)

        added = cfg_locals.revelation()
        config_summary = ConfigSummary(
            added,
            cfg_locals.modified,
            cfg_locals.typechanges,
            cfg_locals.fallback_writes,
            docs=self._var_docs,
        )
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
    func_code = textwrap.dedent("".join(func_code_lines))
    # Lines are now dedented
    func_code_lines = func_code.splitlines(True)
    func_ast = ast.parse(func_code)
    first_code = func_ast.body[0].body[0]
    line_offset = first_code.lineno
    col_offset = first_code.col_offset

    # Add also previous empty / comment lines
    acceptable_tokens = {
        token.NEWLINE,
        token.INDENT,
        token.DEDENT,
        token.COMMENT,
        token.ENDMARKER,
    }
    last_token_type_acceptable = True
    line_offset_fixed = line_offset
    col_offset_fixed = col_offset
    iterator = iter(func_code_lines)
    for parsed_token in generate_tokens(lambda: next(iterator)):

        token_acceptable = parsed_token.type in acceptable_tokens or (
            parsed_token.type == token.NL and last_token_type_acceptable
        )

        # If the token ends after the start of the first code,
        # we have finished
        if parsed_token.end[0] > line_offset or (
            parsed_token.end[0] == line_offset and parsed_token.end[1] >= col_offset
        ):
            break

        if not token_acceptable:
            line_offset_fixed = parsed_token.end[0]
            col_offset_fixed = parsed_token.end[1]

        last_token_type_acceptable = token_acceptable

    func_body = (
        # First line, without first part if needed
        func_code_lines[line_offset_fixed - 1][col_offset_fixed:]
        # Rest of the lines
        + "".join(func_code_lines[line_offset_fixed:])
    )

    return func_body, start_idx + line_offset_fixed


def is_empty_or_comment(line):
    sline = line.strip()
    return sline == "" or sline.startswith("#")


def iscomment(line):
    return line.strip().startswith("#")


def dedent_line(line, indent):
    for i, (line_sym, indent_sym) in enumerate(zip(line, indent)):
        if line_sym != indent_sym:
            start = i
            break
    else:
        start = len(indent)
    return line[start:]


def dedent_function_body(body):
    lines = body.split("\n")
    # find indentation by first line
    indent = ""
    for line in lines:
        if is_empty_or_comment(line):
            continue
        else:
            indent = re.match(r"^\s*", line).group()
            break

    out_lines = [dedent_line(line, indent) for line in lines]
    return "\n".join(out_lines)


def get_function_body_code(func):
    filename = inspect.getfile(func)
    func_body, line_offset = get_function_body(func)
    body_source = dedent_function_body(func_body)
    try:
        body_code = compile(body_source, filename, "exec", ast.PyCF_ONLY_AST)
        body_code = ast.increment_lineno(body_code, n=line_offset)
        body_code = compile(body_code, filename, "exec")
    except SyntaxError as e:
        if e.args[0] == "'return' outside function":
            filename, lineno, _, statement = e.args[1]
            raise SyntaxError(
                "No return statements allowed in ConfigScopes\n"
                "('{}' in File \"{}\", line {})".format(
                    statement.strip(), filename, lineno
                )
            ) from e
        elif e.args[0] == "'yield' outside function":
            filename, lineno, _, statement = e.args[1]
            raise SyntaxError(
                "No yield statements allowed in ConfigScopes\n"
                "('{}' in File \"{}\", line {})".format(
                    statement.strip(), filename, lineno
                )
            ) from e
        else:
            raise
    return body_code


def is_ignored(line):
    for pattern in SETTINGS.CONFIG.IGNORED_COMMENTS:
        if re.match(pattern, line) is not None:
            return True
    return False


def find_doc_for(ast_entry, body_lines):
    lineno = ast_entry.lineno - 1
    line_io = io.BytesIO(body_lines[lineno].encode())
    try:
        tokens = tokenize(line_io.readline) or []
        line_comments = [token.string for token in tokens if token.type == COMMENT]

        if line_comments:
            formatted_lcs = [line[1:].strip() for line in line_comments]
            filtered_lcs = [line for line in formatted_lcs if not is_ignored(line)]
            if filtered_lcs:
                return filtered_lcs[0]
    except TokenError:
        pass

    lineno -= 1
    while lineno >= 0:
        if iscomment(body_lines[lineno]):
            comment = body_lines[lineno].strip("# ")
            if not is_ignored(comment):
                return comment
        if not body_lines[lineno].strip() == "":
            return None
        lineno -= 1
    return None


def add_doc(target, variables, body_lines):
    if isinstance(target, ast.Name):
        # if it is a variable name add it to the doc
        name = target.id
        if name not in variables:
            doc = find_doc_for(target, body_lines)
            if doc is not None:
                variables[name] = doc
    elif isinstance(target, ast.Tuple):
        # if it is a tuple then iterate the elements
        # this can happen like this:
        # a, b = 1, 2
        for e in target.elts:
            add_doc(e, variables, body_lines)


def get_config_comments(func):
    filename = inspect.getfile(func)
    func_body, line_offset = get_function_body(func)
    body_source = dedent_function_body(func_body)
    body_code = compile(body_source, filename, "exec", ast.PyCF_ONLY_AST)
    body_lines = body_source.split("\n")

    variables = {"seed": "the random seed for this experiment"}

    for ast_root in body_code.body:
        for ast_entry in [ast_root] + list(ast.iter_child_nodes(ast_root)):
            if isinstance(ast_entry, ast.Assign):
                # we found an assignment statement
                # go through all targets of the assignment
                # usually a single entry, but can be more for statements like:
                # a = b = 5
                for t in ast_entry.targets:
                    add_doc(t, variables, body_lines)

    return variables
