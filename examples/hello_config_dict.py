#!/usr/bin/env python
# coding=utf-8
""" A configurable Hello World. Yay! """
from __future__ import division, print_function, unicode_literals
from sacred import Experiment

ex = Experiment('hello_config_dict')


ex.add_config(
    message="Hello world!"
)


@ex.automain
def main(message):
    print(message)
