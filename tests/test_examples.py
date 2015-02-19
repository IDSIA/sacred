#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import os
import os.path
import sys
import pytest
import shlex

EXAMPLES_PATH = os.path.abspath('examples')
sys.path.append(EXAMPLES_PATH)
examples = [f.strip('.py') for f in os.listdir(EXAMPLES_PATH)
            if os.path.isfile(os.path.join(EXAMPLES_PATH, f))]


def get_calls_from_doc(doc):
    if doc is None:
        return []
    calls = []
    outputs = []
    out = []
    for l in doc.split('\n'):
        if l.startswith('  $'):
            calls.append(shlex.split(l[3:]))
            out = []
            outputs.append(out)
        elif l.startswith('  '):
            out.append(l[2:])
        else:
            out = []

    return zip(calls, outputs)


@pytest.mark.parametrize("example_name", examples)
def test_hello_config_dict(capsys, example_name):
    example = __import__(example_name)
    calls_outs = get_calls_from_doc(example.__doc__)
    for call, out in calls_outs:
        r = example.ex.run_commandline(call)
        captured_out, captured_err = capsys.readouterr()
        captured_out = captured_out.split('\n')
        captured_err = captured_err.split('\n')
        for out_line in out:
            assert out_line == captured_out[0] or out_line == captured_err[0]
            if out_line == captured_out[0]:
                captured_out.pop(0)
            else:
                captured_err.pop(0)
        assert captured_out == ['']
        assert captured_err == ['']

