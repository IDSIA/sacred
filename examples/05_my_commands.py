#!/usr/bin/env python
# coding=utf-8
"""
This experiment showcases the concept of commands in Sacred.
By just using the ``@ex.command`` decorator we can add additional commands to
the command-line interface of the experiment::

  $ ./05_my_commands.py greet
  WARNING - my_commands - No observers have been added to this run
  INFO - my_commands - Running command 'greet'
  INFO - my_commands - Started
  Hello John! Nice to greet you!
  INFO - my_commands - Completed after 0:00:00

::

  $ ./05_my_commands.py shout
  WARNING - my_commands - No observers have been added to this run
  INFO - my_commands - Running command 'shout'
  INFO - my_commands - Started
  WHAZZZUUUUUUUUUUP!!!????
  INFO - my_commands - Completed after 0:00:00

Of course we can also use ``with`` and other flags with those commands::

  $ ./05_my_commands.py greet with name='Jane' -l WARNING
  WARNING - my_commands - No observers have been added to this run
  Hello Jane! Nice to greet you!

In fact, the main function is also just a command::

  $ ./05_my_commands.py main
  WARNING - my_commands - No observers have been added to this run
  INFO - my_commands - Running command 'main'
  INFO - my_commands - Started
  This is just the main command. Try greet or shout.
  INFO - my_commands - Completed after 0:00:00

Commands also appear in the help text, and you can get additional information
about all commands using ``./05_my_commands.py help [command]``.
"""

from __future__ import division, print_function, unicode_literals
from sacred import Experiment

ex = Experiment('my_commands')


@ex.config
def cfg():
    name = 'John'


@ex.command
def greet(name):
    """
    Print a nice greet message.

    Uses the name from config.
    """
    print('Hello {}! Nice to greet you!'.format(name))


@ex.command
def shout():
    """
    Shout slang question for "what is up?"
    """
    print('WHAZZZUUUUUUUUUUP!!!????')


@ex.automain
def main():
    print('This is just the main command. Try greet or shout.')
