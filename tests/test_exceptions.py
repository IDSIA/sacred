#!/usr/bin/env python
# coding=utf-8

import re

from sacred import Ingredient, Experiment
from sacred.utils import (
    CircularDependencyError,
    ConfigAddedError,
    MissingConfigError,
    NamedConfigNotFoundError,
    format_filtered_stacktrace,
    format_sacred_error,
    SacredError,
)

"""Global Docstring"""

import pytest


def test_circular_dependency_raises():
    # create experiment with circular dependency
    ing = Ingredient("ing")
    ex = Experiment("exp", ingredients=[ing])
    ex.main(lambda: None)
    ing.ingredients.append(ex)

    # run and see if it raises
    with pytest.raises(CircularDependencyError, match="exp->ing->exp"):
        ex.run()


def test_config_added_raises():
    ex = Experiment("exp")
    ex.main(lambda: None)

    with pytest.raises(
        ConfigAddedError,
        match=r"Added new config entry that is not used anywhere.*\n"
        r"\s*Conflicting configuration values:\n"
        r"\s*a=42",
    ):
        ex.run(config_updates={"a": 42})


def test_missing_config_raises():
    ex = Experiment("exp")
    ex.main(lambda a: None)
    with pytest.raises(MissingConfigError):
        ex.run()


def test_named_config_not_found_raises():
    ex = Experiment("exp")
    ex.main(lambda: None)
    with pytest.raises(
        NamedConfigNotFoundError,
        match='Named config not found: "not_there". ' "Available config values are:",
    ):
        ex.run(named_configs=("not_there",))


def test_format_filtered_stacktrace_true():
    ex = Experiment("exp")

    @ex.capture
    def f():
        raise Exception()

    try:
        f()
    except:
        st = format_filtered_stacktrace(filter_traceback="default")
        assert "captured_function" not in st
        assert "WITHOUT Sacred internals" in st

    try:
        f()
    except:
        st = format_filtered_stacktrace(filter_traceback="always")
        assert "captured_function" not in st
        assert "WITHOUT Sacred internals" in st


def test_format_filtered_stacktrace_false():
    ex = Experiment("exp")

    @ex.capture
    def f():
        raise Exception()

    try:
        f()
    except:
        st = format_filtered_stacktrace(filter_traceback="never")
        assert "captured_function" in st


@pytest.mark.parametrize(
    "print_traceback,filter_traceback,print_usage,expected",
    [
        (False, "never", False, ".*SacredError: message"),
        (
            True,
            "never",
            False,
            r"Traceback \(most recent call last\):\n*"
            r'\s*File ".*", line \d*, in '
            r"test_format_sacred_error\n*"
            r".*\n*"
            r".*SacredError: message",
        ),
        (False, "default", False, r".*SacredError: message"),
        (False, "always", False, r".*SacredError: message"),
        (False, "never", True, r"usage\n.*SacredError: message"),
        (
            True,
            "default",
            False,
            r"Traceback \(most recent calls WITHOUT "
            r"Sacred internals\):\n*"
            r"(\n|.)*"
            r".*SacredError: message",
        ),
        (
            True,
            "always",
            False,
            r"Traceback \(most recent calls WITHOUT "
            r"Sacred internals\):\n*"
            r"(\n|.)*"
            r".*SacredError: message",
        ),
    ],
)
def test_format_sacred_error(print_traceback, filter_traceback, print_usage, expected):
    try:
        raise SacredError("message", print_traceback, filter_traceback, print_usage)
    except SacredError as e:
        st = format_sacred_error(e, "usage")
        assert re.match(expected, st, re.MULTILINE)
