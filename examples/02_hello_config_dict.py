#!/usr/bin/env python
# coding=utf-8
""" A configurable Hello World "experiment".
In this example we configure the message using a dictionary with
``ex.add_config``

You can run it like this::

  $ ./02_hello_config_dict.py
  WARNING - 02_hello_config_dict - No observers have been added to this run
  INFO - 02_hello_config_dict - Running command 'main'
  INFO - 02_hello_config_dict - Started
  Hello world!
  INFO - 02_hello_config_dict - Completed after 0:00:00

The message can also easily be changed using the ``with`` command-line
argument::

  $ ./02_hello_config_dict.py with message='Ciao world!'
  WARNING - 02_hello_config_dict - No observers have been added to this run
  INFO - 02_hello_config_dict - Running command 'main'
  INFO - 02_hello_config_dict - Started
  Ciao world!
  INFO - 02_hello_config_dict - Completed after 0:00:00
"""
from __future__ import division, print_function, unicode_literals
from sacred import Experiment

ex = Experiment()

# We add message to the configuration of the experiment here
ex.add_config({
    "message": "Hello world!"
})
# Equivalent:
# ex.add_config(
#     message="Hello world!"
# )


# notice how we can access the message here by taking it as an argument
@ex.automain
def main(message):
    print(message)
