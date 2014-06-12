#!/usr/bin/python
# coding=utf-8
"""
This is a very basic example of how to use sacred.
"""
from __future__ import division, print_function, unicode_literals
from sacred import Experiment, Module


m1 = Module("dataset")


@m1.config
def cfg():
    basepath = "/home/"
    filename = "foo.hdf5"


@m1.capture
def foo(basepath, filename):
    return basepath + filename


@m1.command
def stats(**config):
    print(config)



ex = Experiment(modules=[m1])


@ex.config
def cfg():
    a = 10
    b = 17
    c = a + b


@ex.capture("dataset")
def load_dataset(filename):
    print(filename)

@ex.automain
def main(a, b, c, dataset):
    print('a =', a)
    print('b =', b)
    print('c =', c)
    m2.foo()
    print(dataset)