#!/usr/bin/env python
# coding=utf-8
"""
This is a very basic example of how to use Sacred.
"""
from __future__ import division, print_function, unicode_literals
from sacred import Experiment, Ingredient

# ============== Ingredient 0: settings =================
s = Ingredient("settings")


@s.config
def cfg1():
    verbose = True


# ============== Ingredient 1: dataset.paths =================
data_paths = Ingredient("dataset.paths", ingredients=[s])


@data_paths.config
def cfg2(settings):
    v = not settings['verbose']
    base = '/home/sacred/'


# ============== Ingredient 2: dataset =======================
data = Ingredient("dataset", ingredients=[data_paths, s])


@data.config
def cfg3(paths):
    basepath = paths['base'] + 'datasets/'
    filename = "foo.hdf5"


@data.capture
def foo(basepath, filename, paths, settings):
    print(paths)
    print(settings)
    return basepath + filename


# ============== Experiment ==============================
ex = Experiment('modular_example', ingredients=[data, data_paths])


@ex.config
def cfg(dataset):
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
    # print("dataset", dataset)
    # print("dataset.paths", dataset['paths'])
    print("foo()", foo())
