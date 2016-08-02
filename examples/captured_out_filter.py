#!/usr/bin/env python
# coding=utf-8
"""
This example shows how to apply a filter function to the captured output
of a run. This is often useful when using progress bars or similar in the text
UI and you don't want to store formatting characters like backspaces and
linefeeds in the database.
"""
from __future__ import division, print_function, unicode_literals

import sys
import time

from sacred import Experiment
from sacred.utils import apply_backspaces_and_linefeeds

ex = Experiment('progress')

# try commenting out the line below to see the difference in captured output
ex.captured_out_filter = apply_backspaces_and_linefeeds


def write_and_flush(*args):
    for arg in args:
        sys.stdout.write(arg)
    sys.stdout.flush()


class ProgressMonitor(object):
    def __init__(self, count):
        self.count, self.progress = count, 0

    def show(self, n=1):
        self.progress += n
        text = 'Completed {}/{} tasks'.format(self.progress, self.count)
        write_and_flush('\b' * 80, '\r', text)

    def done(self):
        write_and_flush('\n')


def progress(items):
    p = ProgressMonitor(len(items))
    for item in items:
        yield item
        p.show()
    p.done()


@ex.main
def main():
    for item in progress(range(100)):
        time.sleep(0.05)


if __name__ == '__main__':
    run = ex.run_commandline()
    print('=' * 80)
    print('Captured output: ', repr(run.captured_out))
