#!/usr/bin/env python
# coding=utf-8
""" A very configurable Hello World. Yay! """
from __future__ import division, print_function, unicode_literals
from sacred import Experiment

ex = Experiment('hello_config')


@ex.named_config
def rude():
    recipient = "bastard"
    message = "Fuck off you {}!".format(recipient)


@ex.config
def cfg():
    recipient = "world"
    message = "Hello {}!".format(recipient)


@ex.automain
def main(message):
    print(__name__)
    print(message)
    return 1/0
