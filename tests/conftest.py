#!/usr/bin/env python
# coding=utf-8

import os.path
import re
import shlex
import sys
import warnings
from imp import reload

from sacred.settings import SETTINGS

EXAMPLES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")
BLOCK_START = re.compile(r"^\s\s+\$.*$", flags=re.MULTILINE)


def get_calls_from_doc(doc):
    """
    Parses a docstring looking for indented blocks that start with $.
    It returns the first lines as call and the rest of the blocks as outputs.
    """
    if doc is None:
        return []
    calls = []
    outputs = []
    out = []
    block_indent = 2
    for l in doc.split("\n"):
        if BLOCK_START.match(l):
            block_indent = l.find("$")
            calls.append(shlex.split(l[block_indent + 1 :]))
            out = []
            outputs.append(out)
        elif l.startswith(" " * block_indent):
            out.append(l[block_indent:])
        else:
            out = []

    return zip(calls, outputs)


def pytest_generate_tests(metafunc):
    # collects all examples and parses their docstring for calls + outputs
    # it then parametrizes the function with 'example_test'
    if "example_test" in metafunc.fixturenames:
        examples = [
            os.path.splitext(f)[0]
            for f in os.listdir(EXAMPLES_PATH)
            if os.path.isfile(os.path.join(EXAMPLES_PATH, f))
            and f.endswith(".py")
            and f != "__init__.py"
            and re.match(r"^\d", f)
        ]

        sys.path.append(EXAMPLES_PATH)
        example_tests = []
        example_ids = []
        for example_name in sorted(examples):
            try:
                example = __import__(example_name)
            except ModuleNotFoundError:
                warnings.warn(
                    "could not import {name}, skips during test.".format(
                        name=example_name
                    )
                )
                continue
            calls_outs = get_calls_from_doc(example.__doc__)
            for i, (call, out) in enumerate(calls_outs):
                example = reload(example)
                example_tests.append((example.ex, call, out))
                example_ids.append("{}_{}".format(example_name, i))
        metafunc.parametrize("example_test", example_tests, ids=example_ids)


def pytest_addoption(parser):
    parser.addoption(
        "--sqlalchemy-connect-url",
        action="store",
        default="sqlite://",
        help="Name of the database to connect to",
    )


# Deactivate GPU info to speed up tests
SETTINGS.HOST_INFO.INCLUDE_GPU_INFO = False
