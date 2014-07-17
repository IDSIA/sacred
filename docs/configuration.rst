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
You can have multiple Config Scopes attached to the same experiment or module.
This is especially useful for overriding module default values (more to that
later). They will be executed in order of declaration. If you want to access
values from a previous scope you have to declare them as parameters to your
function:

.. code-block:: python

    ex = Experiment('multiple_configs_demo')

    @ex.config
    def my_config1():
        a = 10
        b = 'test'

    @ex.config
    def my_config2(a):  # notice the parameter a here
        c = a * 2       # we can use a because we declared it
        a = -1          # we can also change a value
        #d = b + '2'    # error: no access to b

As you'd expect this will result in the configuration
``{'a': -1, 'b': 'test', 'c': 20}``.

Configuration Injection
=======================
Once you've set up your configuration, the next step is to use those values in
the code of the experiment. In order to get the values there ``sacred`` uses a
method called *dependency injection* for configuration values. This means that
it will automatically fill in the missing parameters of all
*captured functions* with configuration values:

.. code-block:: python

    ex = Experiment('captured_func_demo')

    @ex.config
    def my_config1():
        a = 10
        b = 'test'

    @ex.automain
    def my_main(a, b):
        print("a =", a)
        print("b =", b)


Captured Functions
------------------

  - explain ``@ex.capture``
  - ``@ex.main``, ``@ex.automain``, and ``@ex.command`` are also captured functions

Priority
--------

  1. explicitly passed arguments (both positional and keyword)
  2. configuration values
  3. default values

You still get errors for

  - missing values
  - unexpected keyword arguments
  - too many positional arguments

Special Values
--------------
These might change, and are not well documented yet:

  - ``seed`` : a seed that is different for every invocation (-> Controlling Randomness)
  - ``rnd`` : a random state seeded with ``seed``
  - ``log`` : a logger for that function
  - ``run`` : the run object for the current run

Modification via Command-Line
=============================

pass