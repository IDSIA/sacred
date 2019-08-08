#!/usr/bin/env python
# coding=utf-8

import inspect
from inspect import Parameter
from collections import OrderedDict
from sacred.utils import MissingConfigError, SignatureError

ARG_TYPES = [
    Parameter.POSITIONAL_ONLY,
    Parameter.POSITIONAL_OR_KEYWORD,
    Parameter.KEYWORD_ONLY,
]
POSARG_TYPES = [Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD]


def get_argspec(f):
    sig = inspect.signature(f)
    args = [n for n, p in sig.parameters.items() if p.kind in ARG_TYPES]
    pos_args = [
        n
        for n, p in sig.parameters.items()
        if p.kind in POSARG_TYPES and p.default == inspect._empty
    ]
    varargs = [
        n for n, p in sig.parameters.items() if p.kind == Parameter.VAR_POSITIONAL
    ]
    # only use first vararg  (how on earth would you have more anyways?)
    vararg_name = varargs[0] if varargs else None

    varkws = [n for n, p in sig.parameters.items() if p.kind == Parameter.VAR_KEYWORD]
    # only use first varkw  (how on earth would you have more anyways?)
    kw_wildcard_name = varkws[0] if varkws else None
    kwargs = OrderedDict(
        [
            (n, p.default)
            for n, p in sig.parameters.items()
            if p.default != inspect._empty
        ]
    )

    return args, vararg_name, kw_wildcard_name, pos_args, kwargs


class Signature:
    """
    Extracts and stores information about the signature of a function.

    name : the functions name
    arguments : list of all arguments
    vararg_name : name of the *args variable
    kw_wildcard_name : name of the **kwargs variable
    positional_args : list of all positional-only arguments
    kwargs : dict of all keyword arguments mapped to their default
    """

    def __init__(self, f):
        self.name = f.__name__
        args, vararg_name, kw_wildcard_name, pos_args, kwargs = get_argspec(f)
        self.arguments = args
        self.vararg_name = vararg_name
        self.kw_wildcard_name = kw_wildcard_name
        self.positional_args = pos_args
        self.kwargs = kwargs

    def get_free_parameters(self, args, kwargs, bound=False):
        expected_args = self._get_expected_args(bound)
        return [a for a in expected_args[len(args) :] if a not in kwargs]

    def construct_arguments(self, args, kwargs, options, bound=False):
        """
        Construct args list and kwargs dictionary for this signature.

        They are created such that:
          - the original explicit call arguments (args, kwargs) are preserved
          - missing arguments are filled in by name using options (if possible)
          - default arguments are overridden by options
          - TypeError is thrown if:
            * kwargs contains one or more unexpected keyword arguments
            * conflicting values for a parameter in both args and kwargs
            * there is an unfilled parameter at the end of this process
        """
        expected_args = self._get_expected_args(bound)
        self._assert_no_unexpected_args(expected_args, args)
        self._assert_no_unexpected_kwargs(expected_args, kwargs)
        self._assert_no_duplicate_args(expected_args, args, kwargs)

        args, kwargs = self._fill_in_options(args, kwargs, options, bound)

        self._assert_no_missing_args(args, kwargs, bound)
        return args, kwargs

    def __str__(self):
        pos_args = self.positional_args
        varg = ["*" + self.vararg_name] if self.vararg_name else []
        kwargs = ["{}={}".format(n, v.__repr__()) for n, v in self.kwargs.items()]
        kw_wc = ["**" + self.kw_wildcard_name] if self.kw_wildcard_name else []
        arglist = pos_args + varg + kwargs + kw_wc
        return "{}({})".format(self.name, ", ".join(arglist))

    def __repr__(self):
        return "<Signature at 0x{1:x} for '{0}'>".format(self.name, id(self))

    def _get_expected_args(self, bound):
        if bound:
            # When called as instance method, the instance ('self') will be
            # passed as first argument automatically, so the first argument
            # should be excluded from the signature during this invocation.
            return self.arguments[1:]
        else:
            return self.arguments

    def _assert_no_unexpected_args(self, expected_args, args):
        if not self.vararg_name and len(args) > len(expected_args):
            unexpected_args = args[len(expected_args) :]
            raise SignatureError(
                "{} got unexpected argument(s): {}".format(self.name, unexpected_args)
            )

    def _assert_no_unexpected_kwargs(self, expected_args, kwargs):
        if self.kw_wildcard_name:
            return
        unexpected_kwargs = set(kwargs) - set(expected_args)
        if unexpected_kwargs:
            raise SignatureError(
                "{} got unexpected kwarg(s): {}".format(
                    self.name, sorted(unexpected_kwargs)
                )
            )

    def _assert_no_duplicate_args(self, expected_args, args, kwargs):
        positional_arguments = expected_args[: len(args)]
        duplicate_arguments = [v for v in positional_arguments if v in kwargs]
        if duplicate_arguments:
            raise SignatureError(
                "{} got multiple values for argument(s) {}".format(
                    self.name, duplicate_arguments
                )
            )

    def _fill_in_options(self, args, kwargs, options, bound):
        free_params = self.get_free_parameters(args, kwargs, bound)
        new_kwargs = dict(kwargs) if free_params else kwargs
        for param in free_params:
            if param in options:
                new_kwargs[param] = options[param]
        return args, new_kwargs

    def _assert_no_missing_args(self, args, kwargs, bound):
        free_params = self.get_free_parameters(args, kwargs, bound)
        missing_args = [m for m in free_params if m not in self.kwargs]
        if missing_args:
            raise MissingConfigError(
                "{} is missing value(s):".format(self.name),
                missing_configs=missing_args,
            )
