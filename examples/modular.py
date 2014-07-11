#!/usr/bin/python
# coding=utf-8
"""
This is a very basic example of how to use sacred.
"""
from __future__ import division, print_function, unicode_literals
from sacred import Experiment, Module


m0 = Module("paths")


@m0.config
def cfg():
    base = '/home/'

m1 = Module("dataset", modules=[m0])


@m1.config
def cfg():
    basepath = paths['base'] + 'greff/'
    filename = "foo.hdf5"
    paths['base'] += 'blahhaaa'


@m1.capture
def foo(basepath, filename):
    return basepath + filename


# @m1.command
# def stats(**config):
#     print(config)



ex = Experiment(modules=[m0, m1])


@ex.config
def cfg(seed):
    d = seed
    a = 10
    b = 17
    c = a + b


@ex.automain
def main(a, b, c, dataset, paths):
    print('a =', a)
    print('b =', b)
    print('c =', c)
    print("foo()", foo())
    print(dataset)
    print(paths)