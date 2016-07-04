#!/usr/bin/env python
# coding=utf-8
"""
This is a minimal example of a Sacred experiment.

Not much to see here. But it comes with a command-line interface and can be
called like this::

  $ ./01_hello_world.py
  WARNING - 01_hello_world - No observers have been added to this run
  INFO - 01_hello_world - Running command 'main'
  INFO - 01_hello_world - Started
  Hello world!
  INFO - 01_hello_world - Completed after 0:00:00

As you can see it prints 'Hello world!' as expected, but there is also some
additional logging. The log-level can be controlled using the ``-l`` argument::

  $ ./01_hello_world.py -l WARNING
  WARNING - 01_hello_world - No observers have been added to this run
  Hello world!

If you want to learn more about the command-line interface try
``help`` or ``-h``.
"""
from __future__ import division, print_function, unicode_literals
from sacred import Experiment

# Create an Experiment instance
ex = Experiment()


# This function should be executed so we are decorating it with @ex.automain
@ex.automain
def main():
    print('Hello world!')
