#!/usr/bin/env python
# coding=utf-8

import logging


# example_test will be parametrized by the test generation hook in conftest.py
def test_example(capsys, example_test):
    # pytest adds a `LogCaptureHandler` to the root logger. This conflicts
    # with the sacred logger setup, so remove it
    logging.root.handlers = []
    ex, call, out = example_test
    ex.run_commandline(call)
    captured_out, captured_err = capsys.readouterr()
    print(captured_out)
    print(captured_err)
    captured_out = captured_out.split("\n")
    captured_err = captured_err.split("\n")
    for out_line in out:
        assert out_line in [captured_out[0], captured_err[0]]
        if out_line == captured_out[0]:
            captured_out.pop(0)
        else:
            captured_err.pop(0)
    assert captured_out == [""]
    assert captured_err == [""]
