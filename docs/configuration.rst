.. _configuration:

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
    restrictions apply. The keys of all dictionaries cannot contain
    ``.``, ``=``, or ``$``.
    Furthermore they cannot be ``jsonpickle`` keywords like ``py/object``.
    If absolutely necessary, these restrictions can be configured in
    ``sacred.settings.SETTINGS.CONFIG``.

Defining a Configuration
========================
Sacred provides several ways to define a configuration for an experiment.
The most powerful one are Config Scopes, but it is also possible to use plain
dictionaries or config files.


.. _config_scopes:

Config Scopes
-------------

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
        """This is my demo configuration"""

        a = 10  # some integer

        # a dictionary
        foo = {
            'a_squared': a**2,
            'bar': 'my_string%d' % a
        }
        if a > 8:
            # cool: a dynamic entry
            e = a/2

    @ex.main
    def run():
        pass

This config scope would return the following configuration, and in fact, if you
want to play around with this you can just execute ``my_config``::

    >>> my_config()
    {'foo': {'bar': 'my_string10', 'a_squared': 100}, 'a': 10, 'e': 5}

Or use the ``print_config`` command from the :doc:`command_line`::

    $ python config_demo.py print_config
    INFO - config_demo - Running command 'print_config'
    INFO - config_demo - Started
    Configuration (modified, added, typechanged, doc):
      """This is my demo configuration"""
      a = 10                             # some integer
      e = 5.0                            # cool: a dynamic entry
      seed = 954471586                   # the random seed for this experiment
      foo:                               # a dictionary
        a_squared = 100
        bar = 'my_string10'
    INFO - config_demo - Completed after 0:00:00

Notice how Sacred picked up on the doc-string and the line comments used in the
configuration. This can be used to improve user-friendliness of your script.



.. warning::
    Functions used as a config scopes **cannot** contain any ``return`` or
    ``yield`` statements!


.. _config_dictionaries:

Dictionaries
------------
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
------------
If you prefer, you can also directly load configuration entries from a file:

.. code-block:: python

    ex.add_config('conf.json')
    ex.add_config('conf.pickle')  # if configuration was stored as dict
    ex.add_config('conf.yaml')    # requires PyYAML

This will essentially just read the file and add the resulting dictionary to
the configuration with ``ex.add_config``.

.. _multiple_config_scopes:

Combining Configurations
------------------------
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

    ex.add_config({'e': 'from_dict'})
    # could also add a config file here

As you'd expect this will result in the configuration
``{'a': -1, 'b': 'test', 'c': 20, 'e': 'from_dict'}``.



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
    {'foo': {'bar': 'my_string23', 'a_squared': 529}, 'a': 23, 'e': 11.5}


Using the :doc:`command_line` we can achieve the same thing::

    $ python config_demo.py print_config with a=6
    INFO - config_demo - Running command 'print_config'
    INFO - config_demo - Started
    Configuration (modified, added, typechanged, doc):
      a = 6                              # some integer
      seed = 681756089                   # the random seed for this experiment
      foo:                               # a dictionary
        a_squared = 36
        bar = 'my_string6'
    INFO - config_demo - Completed after 0:00:00

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

or from the commandline using dotted notation::

    $ config_demo.py print_config with foo.bar=baobab
    INFO - config_demo - Running command 'print_config'
    INFO - config_demo - Started
    Configuration (modified, added, typechanged, doc):
      a = 10                             # some integer
      e = 5.0                            # cool: a dynamic entry
      seed = 294686062                   # the random seed for this experiment
      foo:                               # a dictionary
        a_squared = 100
        bar = 'baobab'
    INFO - config_demo - Completed after 0:00:00


To prevent accidentally wrong config updates sacred implements a few basic
checks:

  * If you change the type of a config entry it will issue a warning
  * If you add a new config entry but it is used in some captured function, it will issue a warning
  * If you add a new config entry that is not used anywhere it will raise a KeyError.



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


Configuration files can also serve as named configs. Just specify the name of
the file and Sacred will read it and treat it as a named configuration.
Like this::

    $ python named_configs_demo.py with my_variant.json

or this:

.. code-block:: python

    >> ex.run(named_configs=['my_variant.json'])

Where the format of the config file can be anything that is also supported for
:ref:`config files <config_files>`.


.. _configuration_injection:

Accessing Config Entries
========================
Once you've set up your configuration, the next step is to use those values in
the code of the experiment. To make this as easy as possible Sacred
automatically fills in the missing parameters of a *captured function* with
configuration values. So for example this would work:

.. code-block:: python

    ex = Experiment('captured_func_demo')

    @ex.config
    def my_config1():
        a = 10
        b = 'test'

    @ex.automain
    def my_main(a, b):
        print("a =", a)  # 10
        print("b =", b)  # test

.. _captured_functions:

Captured Functions
------------------
Sacred automatically injects configuration values for captured functions.
Apart from the main function (marked by ``@ex.main`` or ``@ex.automain``) this
includes all functions marked with ``@ex.capture``. So the following example
works as before:

.. code-block:: python

    ex = Experiment('captured_func_demo2')

    @ex.config
    def my_config1():
        a = 10
        b = 'test'

    @ex.capture
    def print_a_and_b(a, b):
        print("a =", a)
        print("b =", b)

    @ex.automain
    def my_main():
        print_a_and_b()

Notice that we did not pass any arguments to ``print_a_and_b`` in ``my_main``.
These are filled in from the configuration. We can however override these values
in any way we like:

.. code-block:: python

    @ex.automain
    def my_main():
        print_a_and_b()          # prints '10' and 'test'
        print_a_and_b(3)         # prints '3'  and 'test'
        print_a_and_b(3, 'foo')  # prints '3'  and 'foo'
        print_a_and_b(b='foo')   # prints '10' and 'foo'


.. note::
    All functions decorated with ``@ex.main``, ``@ex.automain``, and
    ``@ex.command`` are also captured functions.


In case of multiple values for the same parameter the priority is:
  1. explicitly passed arguments (both positional and keyword)
  2. configuration values
  3. default values

You will still get an appropriate error in the following cases:
    - missing value that is not found in configuration
    - unexpected keyword arguments
    - too many positional arguments

.. note::
    Be careful with naming your parameters, because configuration injection can
    hide some missing value errors from you, by (unintentionally) filling them
    in from the configuration.

.. note::
    Configuration values should not be changed in a captured function
    because those changes cannot be recorded by the sacred experiment and can
    lead to confusing and unintended behaviour.
    Sacred will raise an Exception if you try to write to a nested
    configuration item. You can disable this (not recommended) by setting
    ``SETTINGS.CONFIG.READ_ONLY_CONFIG = False``.

.. _special_values:

Special Values
--------------
There are a couple of special parameters that captured functions can accept.
These might change, and are not well documented yet, so be careful:

  - ``_config`` : the whole configuration dict that is accessible for this function
  - ``_seed`` : a seed that is different for every invocation (-> Controlling Randomness)
  - ``_rnd`` : a random state seeded with ``seed``
  - ``_log`` : a logger for that function
  - ``_run`` : the run object for the current run


Prefix
------
If you have some function that only needs to access some sub-dictionary of
your configuration you can use the ``prefix`` parameter of ``@ex.capture``:

.. code-block:: python

    ex = Experiment('prefix_demo')

    @ex.config
    def my_config1():
        dataset = {
            'filename': 'foo.txt',
            'path': '/tmp/'
        }

    @ex.capture(prefix='dataset')
    def print_me(filename, path):  # direct access to entries of the dataset dict
        print("filename =", filename)
        print("path =", path)

That way you have direct access to the items of that dictionary, but no access
to the rest of the configuration anymore. It is a bit like setting a namespace
for the function. Dotted notation for the prefix works as you would expect.
