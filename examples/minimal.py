#!/usr/bin/env python
# coding=utf-8
"""
This is a very basic example of how to use sacred.
"""
from __future__ import division, print_function, unicode_literals
from sacred import Experiment

ex = Experiment()


@ex.config
def cfg():
    a = 10
    b = 17
    c = a + b


@ex.automain
def main(a, b, c):
    print('a =', a)
    print('b =', b)
    print('c =', c)


