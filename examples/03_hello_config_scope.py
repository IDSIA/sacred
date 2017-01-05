#!/usr/bin/env python
# coding=utf-8
"""
A configurable Hello World "experiment".
In this example we configure the message using Sacreds special ``ConfigScope``.

As with hello_config_dict you can run it like this::

  $ ./03_hello_config_scope.py
  WARNING - hello_cs - No observers have been added to this run
  INFO - hello_cs - Running command 'main'
  INFO - hello_cs - Started
  Hello world!
  INFO - hello_cs - Completed after 0:00:00

The message can also easily be changed using the ``with`` command-line
argument::

  $ ./03_hello_config_scope.py with message='Ciao world!'
  WARNING - hello_cs - No observers have been added to this run
  INFO - hello_cs - Running command 'main'
  INFO - hello_cs - Started
  Ciao world!
  INFO - hello_cs - Completed after 0:00:00


But because we are using a ``ConfigScope`` that constructs the message from a
recipient we can also just modify that::

  $ ./03_hello_config_scope.py with recipient='Bob'
  WARNING - hello_cs - No observers have been added to this run
  INFO - hello_cs - Running command 'main'
  INFO - hello_cs - Started
  Hello Bob!
  INFO - hello_cs - Completed after 0:00:00
"""
from __future__ import division, print_function, unicode_literals
from sacred import Experiment

ex = Experiment('hello_cs')  # here we name the experiment explicitly


# A ConfigScope is a function like this decorated with @ex.config
# All local variables of this function will be put into the configuration
@ex.config
def cfg():
    # The recipient of the greeting
    recipient = "world"

    # The message used for greeting
    message = "Hello {}!".format(recipient)


# again we can access the message here by taking it as an argument
@ex.automain
def main(message):
    print(message)
