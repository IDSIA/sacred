#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from sacred import Experiment

ex = Experiment('hello_config_scope')


# A ConfigScope is a function like this decorated with @ex.config
# All local variables of this function will be put into the configuration
@ex.config
def cfg():
    recipient = "world"
    message = "Hello %s!" % recipient


@ex.pre_run
def foobar(command_name, config_updates, named_configs):
    print('FOOOOBAR:', command_name)
    config_updates['recipient'] = 'FOOO'
    return command_name, config_updates, named_configs


# again we can access the message here by taking it as an argument
@ex.automain
def main(message):
    print(message)
