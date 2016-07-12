Configuration
*************
The configuration of an experiment is the standard way of parametrizing runs.
It is saved in the database for every run, and can very easily be adjusted.
Furthermore all configuration entries can be accessed by all
:ref:`captured_functions`.

There are three different ways of adding configuration to an experiment.
Through :ref:`config_scopes`, :ref:`config_dictionaries`, and
:ref:`config_files`

.. note::
    Because configuration entries are saved to the database directly, some
    restrictions apply. First of all only objects that are JSON-serializable
    can be part of the configuration. Also the keys of all dictionaries have
    to be strings, and they cannot contain ``.`` or ``$``.

.. _config_scopes:

Config Scopes
=============

A Config Scope is just a regular function decorated with ``@ex.config``. It
is executed by Sacred just before running the experiment. All variables from
its local scope are then collected, and become configuration entries of the
experiment. Inside that function you have full access to all features of python
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

    @ex.main
    def run():
        pass

This config scope would return the following configuration, and in fact, if you
want to play around with this you can just execute ``my_config``::

    >>> my_config()
    {'foo': {'bar': 'my_string10', 'a_squared': 100}, 'a': 10, 'e': 5}

Or use the ``print_config`` command from the :doc:`command-line`::

    $ python config_demo.py print_config
    INFO - config_demo - Running command 'print_config'
    INFO - config_demo - started
    Configuration:
      a = 10
      e = 5
      seed = 746486301
      foo:
        a_squared = 100
        bar = 'my_string10'
    INFO - config_demo - finished after 0:00:00.


All variables that are **not** JSON serializable inside a config scope are
ignored. So the following config scope would result in an empty configuration:

.. code-block:: python

    @ex.config
    def empty_config():
        import re                           # not JSON serializable
        pattern = re.compile('[iI]gnored')   # not JSON serializable
        match = pattern.match('this is ignored')  # not JSON serializable


.. warning::
    Functions used as a config scopes **cannot** contain any ``return`` or
    ``yield`` statements!


.. _config_dictionaries:

Dictionaries
============
Configuration entries can also directly be added as a dictionary using the
``ex.add_config`` method:

.. code-block:: python

    ex.add_config({
      'foo': 42,
      'bar': 'baz
    })

Or equivalently:

.. code-block:: python

    ex.add_config(
        foo=42,
        bar='baz'
    )

Unlike config scopes, this method raises an error if you try to add any object,
that is not JSON-Serializable.

.. _config_files:

Config Files
============
If you prefer, you can also directly load configuration entries from a file:

.. code-block:: python

    ex.add_config('conf.json')
    ex.add_config('conf.pickle')  # if configuration was stored as dict
    ex.add_config('conf.yaml')  # requires PyYAML

This will essentially just read the file and add the resulting dictionary to
the configuration with ``ex.add_config``.

.. _updating_values:

Updating Config Entries
=======================
When an experiment is run, the configuration entries can be updated by passing
an update dictionary. So let's recall this experiment to see how that works:

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

    @ex.main
    def run():
        pass

If we run that experiment from python we can simply pass a ``config_updates``
dictionary:

.. code-block:: python

    >>> r = ex.run(config_updates={'a': 23})
    >>> r.config
    {'foo': {'bar': 'my_string23', 'a_squared': 529}, 'a': 23, 'e': 5}


Using the :doc:`command-line` we can achieve the same thing::

    $ config_demo.py print_config with a=6
    INFO - config_demo - Running command 'print_config'
    INFO - config_demo - started
    Configuration:
      a = 6
      e = 5
      seed = 746486301
      foo:
        a_squared = 36
        bar = 'my_string6'
    INFO - config_demo - finished after 0:00:00.

Note that because we used a config scope all the values that depend on ``a``
change accordingly.

.. note::
    This might make you wonder about what is going on. So let me briefly explain:
    Sacred extracts the body of the function decorated with ``@ex.config`` and
    runs it using the ``exec`` statement. That allows it to provide a ``locals``
    dictionary which can block certain changes and log all the others.

We can also fix any of the other values, even nested ones:

.. code-block:: python

    >>> r = ex.run(config_updates={'foo': {'bar': 'baobab'}})
    >>> r.config
    {'foo': {'bar': 'baobab', 'a_squared': 100}, 'a': 10, 'e': 5}

To prevent accidentally wrong config updates sacred implements a few basic
checks:

  * If you change the type of a config entry it will issue a warning
  * If you add a new config entry but that is used in some captured function, it will issue a warning
  * If you add a new config entry that is not used anywhere it will raise a KeyError.

.. _multiple_config_scopes:

Multiple Config Scopes
======================
You can have multiple Config Scopes and/or Dictionaries and/or Files attached
to the same experiment or ingredient.
They will be executed in order of declaration.
This is especially useful for overriding ingredient default values (more about that
later).
In config scopes you can even access the earlier configuration entries, by just
declaring them as parameters in your function:

.. code-block:: python

    ex = Experiment('multiple_configs_demo')

    @ex.config
    def my_config1():
        a = 10
        b = 'test'

    @ex.config
    def my_config2(a):  # notice the parameter a here
        c = a * 2       # we can use a because we declared it
        a = -1          # we can also change the value of a
        #d = b + '2'    # error: no access to b

As you'd expect this will result in the configuration
``{'a': -1, 'b': 'test', 'c': 20}``.

.. _named_configurations:

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

    $ python named_configs_demo.py with variant1

Or like this:

.. code-block:: python

    >> ex.run(named_configs=['variant1'])

Then the configuration becomes ``{'a':100, 'b':300, 'c':"bar"}``. Note that the
named ConfigScope is run first and its values are treated as fixed, so you can
have other values that are computed from them.

.. note::
    You can have multiple named configurations, and you can use as many of them
    as you like for any given run. But notice that the order in which you
    include them matters: The ones you put first will be evaluated first and
    the values they set might be overwritten by further named configurations.
