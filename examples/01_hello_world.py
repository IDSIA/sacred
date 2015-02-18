#!/usr/bin/env python
# coding=utf-8
"""
This is a minimal example of a sacred experiment.

Not much to see here. But it comes with a commandline interface and can be
called like this:

>>$ ./01_hello_world.py
  INFO - hello_world - Running command 'main'
  INFO - hello_world - Started
  Hello world!
  INFO - hello_world - Completed after 0:00:00

As you can see it prints 'Hello world!' as expected, but there is also some
additional logging. The log-level can be controlled using the -l argument:

>>$ ./01_hello_world.py -l ERROR
  Hello world!

If you want to learn more about the commandline interface try help or -h.
"""
from __future__ import division, print_function, unicode_literals
from sacred import Experiment

# Create an Experiment instance and provide it with a name
ex = Experiment('hello_world')


# This function should be executed so we are decorating it with @ex.automain
@ex.automain
def main():
    print('Hello world!')
