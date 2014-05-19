#!/usr/bin/env python
# coding=utf-8
"""
This is a very basic example Experiment using sacred.
"""
from __future__ import division, print_function, unicode_literals
from sacred import Experiment

ex = Experiment()


@ex.config
def cfg():
    a = 10
    b = 17
    c = a + b
    name = "John"


@ex.command
def greet(name):
    """
    Print a nice message.
    Uses the name set in the config.
    """
    print("Hello %s!" % name)


@ex.command
def shout():
    """
    Ask loudly 'What is up?'
    """
    print("WHAZZZZUUUUUUUUUUUP!")

@ex.automain
def main(a, b, c, log):
    log.info("a=%d, b=%d, c=%d" % (a, b, c))

