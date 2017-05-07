#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import os
import sys
from sacred.stdout_capturing import get_stdcapturer
from sacred.optional import libc


def test_python_tee_output(capsys):
    expected_lines = {
        "captured stdout",
        "captured stderr"}

    capture_mode, capture_stdout = get_stdcapturer("sys")
    with capsys.disabled():
        print('before (stdout)')
        print('before (stderr)')
        with capture_stdout() as (f, final_out):
            print("captured stdout")
            print("captured stderr")
            f.seek(0)
            output = f.read()

        print('after (stdout)')
        print('after (stderr)')

        assert set(output.strip().split("\n")) == expected_lines


def test_fd_tee_output(capsys):
    expected_lines = {
        "captured stdout",
        "captured stderr",
        "and this is from echo"}
    if not sys.platform.startswith('win'):
        # FIXME: this line randomly doesn't show on windows (skip for now)
        expected_lines.add("stdout from C")

    capture_mode, capture_stdout = get_stdcapturer("fd")
    with capsys.disabled():
        print('before (stdout)')
        print('before (stderr)')
        with capture_stdout() as (f, final_out):
            print("captured stdout")
            print("captured stderr")
            if not sys.platform.startswith('win'):
                libc.puts(b'stdout from C')
                libc.fflush(None)
            os.system('echo and this is from echo')
            f.seek(0)
            output = f.read().decode()

        print('after (stdout)')
        print('after (stderr)')

        assert set(output.strip().split("\n")) == expected_lines
