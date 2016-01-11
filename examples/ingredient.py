#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from sacred import Ingredient, Experiment

# ================== Dataset Ingredient =======================================
# could be in a separate file

data_ingredient = Ingredient('dataset')


@data_ingredient.config
def cfg1():
    filename = 'my_dataset.npy'
    normalize = True


@data_ingredient.capture
def load_data(filename, normalize):
    print("loading dataset from '{}'".format(filename))
    if normalize:
        print("normalizing dataset")
        return 1
    return 42


@data_ingredient.command
def stats(filename, foo=12):
    print('Statistics for dataset "{}":'.format(filename))
    print('mean = 42.23')
    print('foo=', foo)


# ================== Experiment ===============================================

@data_ingredient.config
def cfg2():
    filename = 'foo.npy'

# add the Ingredient while creating the experiment
ex = Experiment('my_experiment', ingredients=[data_ingredient])


@ex.automain
def run():
    data = load_data()  # just use the function
    print('data={}'.format(data))
