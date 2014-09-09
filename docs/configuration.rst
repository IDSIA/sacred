Config Scopes
*************
A Config Scope is just a regular function decorated with ``@ex.config``. It
is executed by Sacred just before running the experiment. Then all the
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
=============
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
==============
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


.. _multiple_config_scopes:

Multiple Config Scopes
======================
You can have multiple Config Scopes attached to the same experiment or ingredient.
This is especially useful for overriding ingredient default values (more about that
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

Named Configurations
====================
With so called *Named Configurations* you can provide a ConfigScope that
is not used by default, but can be optionally added as config updates:

.. code-block:: python

    ex = Experiment('named_configs_demo')

    @ex.config
    def cfg():
        a = 10
        b = 3 * a
        c = "foo"

    @ex.named_config
    def variant1():
        a = 100
        c = "bar"

The default configuration of this Experiment is ``{'a':10, 'b':30, 'c':"foo"}``.
But if you run it with the named config like this::

    >> python named_configs_demo.py with variant1

Then the configuration becomes ``{'a':100, 'b':300, 'c':"bar"}``. Note that the
named ConfigScope is run first and its values are treated as fixed, so you can
have other values that are computed from them.

