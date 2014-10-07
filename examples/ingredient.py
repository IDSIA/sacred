#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from sacred import Ingredient, Experiment

# ================== Dataset Ingredient =======================================
# could be in a separate file

data_ingredient = Ingredient('dataset')


@data_ingredient.config
def cfg():
    filename = 'my_dataset.npy'
    normalize = True


@data_ingredient.capture
def load_data(filename, normalize):
    print("loading dataset from '%s'" % filename)
    if normalize:
        print("normalizing dataset")
        return 1
    return 42


@data_ingredient.command
def stats(filename):
    print('Statistics for dataset "%s":' % filename)
    print('mean = 42.23')


# ================== Experiment ===============================================

@data_ingredient.config
def cfg():
    filename = 'foo.npy'

# add the Ingredient while creating the experiment
ex = Experiment('my_experiment', ingredients=[data_ingredient])


@ex.automain
def run():
    data = load_data()  # just use the function
    print('data=%d' % data)
