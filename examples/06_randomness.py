#!/usr/bin/env python
# coding=utf-8
"""
This example showcases the randomness features of Sacred.

Sacred generates a random global seed for every experiment, that you can
find in the configuration. It will be different every time you run the
experiment.

Based on this global seed it will generate the special parameters ``_seed`` and
``_rnd`` for each captured function. Every time you call such a function the
``_seed`` will be different and ``_rnd`` will be differently seeded random
state. But their values depend deterministically on the global seed and on how
often the function has been called.

Here are a couple of things you should try:

  - run the experiment a couple of times and notice how the results are
    different every time

  - run the experiment a couple of times with a fixed seed.
    Notice that the results are the same::

      :$ ./06_randomness.py with seed=12345 -l WARNING
      [57]
      [28]
      695891797
      [82]

  - run the experiment with a fixed seed and vary the numbers parameter.
    Notice that all the results stay the same except for the added numbers.
    This demonstrates that all the calls to one function are in fact
    independent from each other::

      :$ ./06_randomness.py with seed=12345 numbers=3 -l WARNING
      [57, 79, 86]
      [28, 90, 92]
      695891797
      [82, 9, 3]

  - run the experiment with a fixed seed and set the reverse parameter to true.
    Notice how the results are the same, but in slightly different order.
    This shows that calls to different functions do not interfere with one
    another::

      :$ ./06_randomness.py with seed=12345 reverse=True numbers=3 -l WARNING
      695891797
      [57, 79, 86]
      [28, 90, 92]
      [82, 9, 3]

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
