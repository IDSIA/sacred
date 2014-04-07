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


@ex.config
def cfg2():
    d = c*2


@ex.main
def main(a, b, c, d, log):
    log.info("a=%d, b=%d, c=%d, d=%d" % (a, b, c, d))

if __name__ == "__main__":
    ex.run()
