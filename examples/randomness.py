#!/usr/bin/python
# coding=utf-8
"""
An example showcasing the randomness features of Sacred.
Here are a couple of things you should try:
  - run the experiment a couple of times and notice how the results are
    different every time

  - run the experiment a couple of times with a fixed seed:
    >> ./randomness.py with seed=12345
    Notice that the results are the same

  - run the experiment with a fixed seed and vary the numbers parameter:
    >> ./randomness.py with seed=12345 numbers=3
    Notice that all the results stay the same except for the added numbers.
    This shows that the different calls to a function are in fact independent
    from each other.

  - run the experiment with a fixed seed and set the reverse parameter to true:
    >> ./randomness.py with seed=12345 reverse=True
    Notice how the results are the same, but in slightly different order.
    This shows that the calls to different functions do not interfere with one
    another.
"""
from __future__ import division, print_function, unicode_literals
from sacred import Experiment

ex = Experiment('randomness')


@ex.config
def cfg():
    reverse = False
    numbers = 1


@ex.capture
def do_random_stuff(numbers, _rnd):
    print([_rnd.randint(1, 100) for _ in range(numbers)])


@ex.capture
def do_more_random_stuff(_seed):
    print(_seed)


@ex.automain
def run(reverse):
    if reverse:
        do_more_random_stuff()
        do_random_stuff()
        do_random_stuff()
    else:
        do_random_stuff()
        do_random_stuff()
        do_more_random_stuff()

    do_random_stuff()
