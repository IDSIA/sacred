Quickstart
**********

Installation
============
You can get Sacred directly from pypi like this::

    pip install sacred

But you can of course also clone the git repo and install it from there::

    git clone https://github.com/IDSIA/sacred.git
    cd sacred
    [sudo] python setup.py install

Hello World
===========
Let's jump right into it. This is a minimal experiment using Sacred:

.. code-block:: python

    from sacred import Experiment

    ex = Experiment()

    @ex.automain
    def my_main():
        print('Hello world!')

We did three things here:
  - import ``Experiment`` from ``sacred``
  - create an experiment instance ``ex``
  - decorate the function that we want to run with ``@ex.automain``

This experiment can be run from the command-line, and this is what we get::

    > python h01_hello_world.py
    INFO - 01_hello_world - Running command 'my_main'
    INFO - 01_hello_world - Started
    Hello world!
    INFO - 01_hello_world - Completed after 0:00:00


This experiment already has a full command-line interface, that we could use
to control the logging level or to automatically save information about the run
in a database. But all of that is of limited use for an experiment without
configurations.

Our First Configuration
=======================

So let us add some configuration to our program:

.. code-block:: python

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

When we run this experiment, Sacred will run the ``my_config`` function  and
put all variables from its local scope into the configuration of our experiment.
All the variables defined there can then be used in the ``main`` function. We can see
this happening by asking the command-line interface to print the configuration
for us::

    > python hello_config.py print_config
    INFO - hello_config - Running command 'print_config'
    INFO - hello_config - started
    Configuration:
      message = 'Hello world!'
      recipient = 'world'
      seed = 746486301
    INFO - hello_config - finished after 0:00:00.

Notice how Sacred picked up the ``message`` and the ``recipient`` variables.
It also added a ``seed`` to our configuration, but we are going to ignore that
for now.

Now that our experiment has a configuration we can change it from the
:doc:`command_line`::

    > python hello_config.py with recipient="that is cool"
    INFO - hello_config - Running command 'my_main'
    INFO - hello_config - started
    Hello that is cool!
    INFO - hello_config - finished after 0:00:00.

Notice how changing the ``recipient`` also changed the message. This should give
you a glimpse of the power of Sacred. But there is a lot more to it, so keep reading :).
