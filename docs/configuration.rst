Configuration
*************

The ability to conveniently make experiments configurable is at the heart of
``sacred``. If the parameters of an experiment are exposed in a this way, it
will help you to:

    - keep track of all the parameters of your experiment
    - easily run your experiment for different settings
    - save configurations for individual runs in files or a database
    - reproduce your results

In ``sacred`` we achieve this through three main mechanisms:

    1. *Config Scopes* are functions with a ``@ex.config`` decorator, that turn
       all local variables into configuration entries.
    2. Those entries can then be used in *captured functions* via *dependency
       injection*. That way the system takes care of passing parameters around for you.
    3. Finally, the *command-line interface* provides an easy way of modifying
       those parameters


Config Scopes
=============
A Config Scope is just a regular function decorated with ``@ex.config``. It
is executed by ``sacred`` just before running the experiment. Then all the
variables from its local scope are collected, and become the parameters of the
experiment. This means that you have full access to all the features of python
for setting up the parameters:

.. code-block:: python

    from sacred import Experiment
    ex = Experiment('config_demo')

    @ex.config
    def my_config():
        a = 10
        foo = {
            'a_squared': a**2,
            'bar': 'my_string%d' % a
        }
        if a > 8:
            e = a/2

This config scope would return the following configuration, and in fact, if you
want to play around with this you can just execute ``my_config``::

    >>> my_config()
    {'a': 10,
     'e': 5,
     'foo': {'a_squared': 100
             'bar': 'my_string10'}
    }

Fixing Values
-------------
We can also *fix* some value and see how the configuration changes::

    >>> my_config(fixed={'a': 6})
    {'a': 6,
     'foo': {'a_squared': 36
             'bar': 'my_string6'}
    }

Note that all the values that depend on ``a`` change accordingly, while ``a``
itself is being protected from any change.

We can also fix any of the other values, even nested ones::

    >>> my_config(fixed={'foo': {'bar': 'baobab'}})
    {'a': 10,
     'e': 5,
     'foo': {'a_squared': 100
             'bar': 'baobab'}
    }

Ignored Values
--------------
Two kinds of variables inside a config scope are ignored:

    - All variables that are **not** JSON serializable
    - Variables that start with an underscore

So the following config scope would result in an empty configuration:

.. code-block:: python

    @ex.config
    def empty_config():
        import re                           # not JSON serializable
        pattern = re.compile('[iI]gnored')   # not JSON serializable
        _test_string = 'this is ignored'     # starts with an _
        match = pattern.match(_test_string)  # not JSON serializable

Multiple Config Scopes
----------------------
You can have multiple

Captured Functions
==================

pass

Modification via Command-Line
=============================

pass