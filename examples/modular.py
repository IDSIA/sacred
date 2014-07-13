#!/usr/bin/env python
# coding=utf-8
"""
This is a very basic example of how to use sacred.
"""
from __future__ import division, print_function, unicode_literals
from sacred import Experiment, Module

# ============== Module 1: dataset.paths =================
data_paths = Module("dataset.paths")


@data_paths.config
def cfg():
    base = '/home/sacred/'


# ============== Module 2: dataset =======================
data = Module("dataset", modules=[data_paths])


@data.config
def cfg(paths):
    basepath = paths['base'] + 'datasets/'
    filename = "foo.hdf5"


@data.capture
def foo(basepath, filename):
    return basepath + filename


# ============== Experiment ==============================
ex = Experiment(modules=[data, data_paths])


@ex.config
def cfg(seed, dataset):
    s = seed*2
    a = 10
    b = 17
    c = a + b
    out_base = dataset['paths']['base'] + 'outputs/'
    out_filename = dataset['filename'].replace('.hdf5', '.out')



@ex.automain
def main(a, b, c, out_base, out_filename, dataset):
    print('a =', a)
    print('b =', b)
    print('c =', c)
    print('out_base =', out_base, out_filename)
    print("dataset", dataset)
    print("dataset.paths", dataset['paths'])
    print("foo()", foo())
