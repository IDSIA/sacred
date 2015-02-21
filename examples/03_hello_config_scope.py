#!/usr/bin/env python
# coding=utf-8
"""
A configurable Hello World "experiment".
In this example we configure the message using Sacreds special ``ConfigScope``.

As with hello_config_dict you can run it like this::

  $ ./03_hello_config_scope.py
  INFO - hello_config_scope - Running command 'main'
  INFO - hello_config_scope - Started
  Hello world!
  INFO - hello_config_scope - Completed after 0:00:00

The message can also easily be changed using the ``with`` command-line
argument::

  $ ./03_hello_config_scope.py with message='Ciao world!'
  INFO - hello_config_scope - Running command 'main'
  INFO - hello_config_scope - Started
  Ciao world!
  INFO - hello_config_scope - Completed after 0:00:00


But because we are using a ``ConfigScope`` that constructs the message from a
recipient we can also just modify that::

  $ ./03_hello_config_scope.py with recipient='Bob'
  INFO - hello_config_scope - Running command 'main'
  INFO - hello_config_scope - Started
  Hello Bob!
  INFO - hello_config_scope - Completed after 0:00:00
"""
from __future__ import division, print_function, unicode_literals
from sacred import Experiment

ex = Experiment('hello_config_scope')


# A ConfigScope is a function like this decorated with @ex.config
# All local variables of this function will be put into the configuration
@ex.config
def cfg():
    recipient = "world"
    message = "Hello %s!" % recipient


# again we can access the message here by taking it as an argument
@ex.automain
def main(message):
    print(message)
