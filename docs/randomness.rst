Controlling Randomness
**********************
Many experiments rely on some form of randomness. Controlling this randomness is
key to ensure reproducibility of the results. This typically happens by manually
seeding the *Pseudo Random Number Generator (PRNG)*. Sacred can help you manage
this error-prone procedure.

Automatic Seed
==============
Sacred auto-generates a seed for each run as part of the configuration (You
might have noticed it, when printing the configuration of an experiment).
This seed has a different value everytime the experiment is run and is stored
as part part of the configuration. You can easily set it by::

    >>./experiment.py with seed=123

This root-seed is the central place to control randomness, because internally
all other seeds and PRNGs depend on it in a deterministic way.

Global Seeds
============
Upon starting the experiment, sacred automatically sets the global seed of
``random`` and (if installed) ``numpy.random``, ``tensorflow.set_random_seed``, 
``pytorch.manual_seed`` to the auto-generated root-seed of the experiment. 
This means that even if you don't take any further steps, at least the randomness 
stemming from those two libraries is properly seeded.

If you rely on any other library that you want to seed globally you should do
so manually first thing inside your main function. For this you can either take
the argument ``seed`` (the root-seed), or ``_seed`` (a seed generated for this
call of the main function). In this case it doesn't really matter.

Special Arguments
=================
To generate random numbers that are controlled by the root-seed Sacred provides
two special arguments: ``_rnd`` and ``_seed``.
You can just accept them as a parameters in any captured function:

.. code-block:: python

    @ex.capture
    def do_random_stuff(_rnd, _seed):
        print(_seed)
        print(_rnd.randint(1, 100))

``_seed`` is an integer that is different every time the function is called.
Likewise ``_rnd`` is a PRNG that you can directly use to generate random numbers.

.. note::
    If ``numpy`` is installed ``_rnd`` will be a `numpy.random.RandomState <http://docs.scipy.org/doc/numpy/reference/generated/numpy.random.RandomState.html>`_ object.
    Otherwise it will be `random.Random <https://docs.python.org/2/library/random.html>`_ object.

All ``_seed`` and ``_rnd`` instances depend deterministically on the root-seed
so they can be controlled centrally.

Resilience to Change
====================
The way Sacred generates these seeds and PRNGs actually offers some amount of
resilience to changes in your experiment or your program flow. So suppose for
example you have an experiment that has two methods that use randomness:
``A`` and ``B``. You want to run and compare two variants of that experiment:

    1. Only call ``B``.
    2. First call ``A`` and then ``B``.

If you use just a single global PRNG that would mean that for a fixed seed the
call to ``B`` gives different results for the two variants, because the call to
``A`` changed the state of the global PRNG.

Sacred generates these seeds and PRNGS in a hierarchical way. That makes the
calls to ``A`` and ``B`` independent from one another. So ``B`` would give the
same results in both cases.




