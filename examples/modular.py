#!/usr/bin/env python
# coding=utf-8
"""
This is a very basic example of how to use sacred.
"""
from __future__ import division, print_function, unicode_literals
from sacred import Experiment, Module


paths_m = Module("paths")


@paths_m.config
def cfg():
    base = '/home/'

m1 = Module("dataset", modules=[paths_m])


@m1.config
def cfg(paths):
    basepath = paths['base'] + 'greff/'
    filename = "foo.hdf5"


@m1.capture
def foo(basepath, filename):
    return basepath + filename


ex = Experiment(modules=[m1, paths_m])


@ex.config
def cfg(seed):
    d = seed
    a = 10
    b = 17
    c = a + b


@ex.automain
def main(a, b, c, dataset):
    print('a =', a)
    print('b =', b)
    print('c =', c)
    print("foo()", foo())
    print(dataset)