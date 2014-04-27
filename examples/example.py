#!/usr/bin/python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from sacred import Experiment

ex = Experiment()


@ex.config
def cfg():
    a = 10
    b = 17
    c = a + b


@ex.config
def cfg2():
    d = c*2


@ex.automain
def main(a, b, c, d, log):
    log.info("a=%d, b=%d, c=%d, d=%d" % (a, b, c, d))

