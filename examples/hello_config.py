#!/usr/bin/env python
# coding=utf-8
""" A configurable Hello World. Yay! """
from __future__ import division, print_function, unicode_literals
from sacred import Experiment

ex = Experiment('hello_config')


@ex.config
def cfg():
    recipient = "world"
    message = "Hello %s!" % recipient


@ex.automain
def main(message):
    print(message)