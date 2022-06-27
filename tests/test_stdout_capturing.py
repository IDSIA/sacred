#!/usr/bin/env python
# coding=utf-8

import os
import sys
import pytest
from sacred.stdout_capturing import get_stdcapturer
from sacred.optional import libc


def test_python_tee_output(capsys):
    expected_lines = {"captured stdout", "captured stderr"}

    capture_mode, capture_stdout = get_stdcapturer("sys")
    with capsys.disabled():
        print("before (stdout)")
        print("before (stderr)")
        with capture_stdout() as out:
            print("captured stdout")
            print("captured stderr")
        output = out.get()

        print("after (stdout)")
        print("after (stderr)")

        assert set(output.strip().split("\n")) == expected_lines


@pytest.mark.skipif(sys.platform.startswith("win"), reason="does not run on windows")
def test_fd_tee_output(capsys):
    expected_lines = {
        "captured stdout",
        "captured stderr",
        "stdout from C",
        "and this is from echo",
        "keep\rcarriage\rreturns",
    }

    capture_mode, capture_stdout = get_stdcapturer("fd")
    output = ""
    with capsys.disabled():
        print("before (stdout)")
        print("before (stderr)")
        with capture_stdout() as out:
            print("captured stdout")
            print("captured stderr", file=sys.stderr)
            print("keep\rcarriage\rreturns")
            output += out.get()
            libc.puts(b"stdout from C")
            libc.fflush(None)
            os.system("echo and this is from echo")
            output += out.get()

        output += out.get()

        print("after (stdout)")
        print("after (stderr)")

        assert set(output.strip().split("\n")) == expected_lines
