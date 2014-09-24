#!/usr/bin/env python
# coding=utf-8
""" This is a minimal example of a sacred experiment. """
from __future__ import division, print_function, unicode_literals
from sacred import Experiment

ex = Experiment('hello_world')


@ex.automain
def main():
    print('Hello world!')
