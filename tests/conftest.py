#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import os.path
import re
import sys
import shlex

EXAMPLES_PATH = os.path.abspath('examples')
BLOCK_START = re.compile('^\s\s+\$.*$', flags=re.MULTILINE)


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
    for l in doc.split('\n'):
        if BLOCK_START.match(l):
            block_indent = l.find('$')
            calls.append(shlex.split(l[block_indent + 1:]))
            out = []
            outputs.append(out)
        elif l.startswith(' ' * block_indent):
            out.append(l[block_indent:])
        else:
            out = []

    return zip(calls, outputs)


def pytest_generate_tests(metafunc):
    # collects all examples and parses their docstring for calls + outputs
    # it then parametrizes the function with 'example_test'
    if 'example_test' in metafunc.fixturenames:
        examples = [f.strip('.py') for f in os.listdir(EXAMPLES_PATH)
                    if os.path.isfile(os.path.join(EXAMPLES_PATH, f)) and
                    f.endswith('.py')]

        sys.path.append(EXAMPLES_PATH)
        example_tests = []
        example_ids = []
        for example_name in sorted(examples):
            example = __import__(example_name)
            calls_outs = get_calls_from_doc(example.__doc__)
            for i, (call, out) in enumerate(calls_outs):
                example_tests.append((example.ex, call, out))
                example_ids.append('{}_{}'.format(example_name, i))
        metafunc.parametrize('example_test', example_tests, ids=example_ids)
