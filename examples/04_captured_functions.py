#!/usr/bin/env python
# coding=utf-8
"""
In this example the use of captured functions is demonstrated. Like the
main function, they have access to the configuration parameters by just
accepting them as arguments.

When calling a captured function we do not need to specify the parameters that
we want to be taken from the configuration. They will automatically be filled
by Sacred. But we can always override that by passing them in explicitly.

When run, this example will output the following::

  $ ./04_captured_functions.py -l WARNING
  WARNING - captured_functions - No observers have been added to this run
  This is printed by function foo.
  This is printed by function bar.
  Overriding the default message for foo.

"""
from __future__ import division, print_function, unicode_literals

from sacred import Experiment

ex = Experiment('captured_functions')


@ex.config
def cfg():
    message = "This is printed by function {}."


# Captured functions have access to all the configuration parameters
@ex.capture
def foo(message):
    print(message.format('foo'))


@ex.capture
def bar(message):
    print(message.format('bar'))


@ex.automain
def main():
    foo()  # Notice that we do not pass message here
    bar()  # or here
    # But we can if we feel like it...
    foo('Overriding the default message for {}.')
