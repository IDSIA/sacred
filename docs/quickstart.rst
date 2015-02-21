Quickstart
**********

Installation
============
Should be as easy as this::

    pip install sacred

But you can of course also clone the git repo and install it from there::

    git clone https://github.com/Qwlouse/sacred.git


Hello World
===========
Let's jump right into it. This is a minimal experiment using Sacred:

.. code-block:: python

    """ This is a minimal example of a Sacred experiment """
    from sacred import Experiment

    ex = Experiment('hello_world')

    @ex.automain
    def my_main():
        print('Hello world!')


We did three things here:
  - import ``Experiment`` from ``sacred``
  - create an experiment instance ``ex`` and pass it the name 'hello_world'
  - decorate the function that we want to run with ``@ex.automain``

This experiment can be run from the command-line, and this is what we get::

    > python hello_world.py

    INFO - .main - started
    Hello World!
    INFO - .main - finished after 0:00:00.

Our experiment already has a full command-line interface, that we could use
to control the logging level or to automatically save information about the run
in a database. But all of that is of limited use for an experiment without
configurations.

Our First Configuration
=======================

So let us look at the true strength of Sacred, and add some
configuration to our program:

.. code-block:: python

    """ A configurable hello world program. Yay! """
    from sacred import Experiment

    ex = Experiment('hello_config')

    @ex.config
    def my_config():
        recipient = "world"
        message = "Hello %s!" % recipient

    @ex.automain
    def my_main(message):
        print(message)

If we run this the output will look precisely as before, but there is a lot
going on already, so lets look at what we did:

  - add the ``my_config`` function and decorate it with ``@ex.config``.
  - within that function define the variable ``message``
  - add the ``message`` parameter to the function ``main`` and use it instead of "Hello world!"

When we run this experiment, Sacred will turn the local scope of our
``my_config`` function into the configuration of our experiment. All the
variables defined there can then be used in the ``main`` function. We can see
this happening by asking the command-line interface to print the configuration
for us::

    > python hello_config.py print_config

    INFO - hello_config - Running command 'print_config'
    INFO - .print_config - started
    Configuration:
      message = 'Hello World!'
      recipient = 'World'
      seed = 746486301
    INFO - .print_config - finished after 0:00:00.

Notice how Sacred picked up the ``message`` and the ``recipient`` variables.
It also added a ``seed`` to our configuration, but we are going to ignore that
for now.

Now that our experiment has a configuration we can change it from the
:doc:`command-line`::

    > python hello_config.py with recipient="that is cool"

    INFO - .main - started
    Hello that is cool!
    INFO - .main - finished after 0:00:00.

Notice how changing the ``recipient`` also changed the message. This should give
you a glimpse of the power of Sacred. But there is a lot more to it, so stay
tuned :).
