#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import os
import os.path
import sys
import pytest

EXAMPLES_PATH = os.path.abspath('examples')
sys.path.append(EXAMPLES_PATH)
examples = [f for f in os.listdir(EXAMPLES_PATH)
            if os.path.isfile(os.path.join(EXAMPLES_PATH, f))]


def get_calls_from_doc(doc):
    if doc is None:
        return []
    calls = []
    outputs = []
    errs = []
    out = []
    err = []
    for l in doc.split('\n'):
        if l.startswith('>>$'):
            calls.append(l[3:].strip().split())
            out = []
            outputs.append(out)
            err = []
            errs.append(err)
        elif l.startswith('    '):
            out.append(l.strip())
        elif l.startswith('E   '):
            err.append(l[1:].strip())
        else:
            out = []
            err = []

    return zip(calls, outputs, errs)


@pytest.mark.parametrize("example_name", examples)
def test_hello_config_dict(capsys, example_name):
    example = __import__(example_name.strip('.py'))
    calls_outs = get_calls_from_doc(example.__doc__)
    for call, out, err in calls_outs:
        r = example.ex.run_commandline(call)
        captured_out, captured_err = capsys.readouterr()
        assert captured_out.strip() == "\n".join(out)
        assert captured_err.strip() == "\n".join(err)
