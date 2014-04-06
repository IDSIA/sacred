#!/usr/bin/python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from sperment import Experiment

ex = Experiment()


@ex.config
def cfg():
    a = 10
    b = 17
    c = a + b


@ex.main
def main(a, b, c, log):
    log.info("a=%d, b=%d, c=%d" % (a, b, c))

if __name__ == "__main__":
    ex.run()
