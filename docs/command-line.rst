Command-Line Interface
**********************

Sacred provides a powerful command-line interface for every experiment out of
box. All you have to do to use it is to either have a method decorated with
``@ex.automain`` or to put this block at the end of your file:

.. code-block:: python

    if __name__ == '__main__':
        ex.run_commandline()


Configuration Updates
=====================
You can easily change any configuration entry using the powerful
``with`` argument on the command-line. Just put ``with config=update`` after
your experiment call like this::

    >>> ./example.py with 'a=10'

Or even multiple values just separated by a space::

    >>> ./example.py with 'a=2.3' 'b="FooBar"' 'c=True'


.. note::
    The single quotes (``'``) around each statement are to make sure the bash
    does not interfere. In simple cases you can omit them::

       >>> ./example.py with a=-1 b=2.0 c=True

    But be careful especially with strings, because the outermost quotes get
    removed by bash.
    So for example all of the following values will be ``int``::

       >>> ./example.py with a=1 b="2" c='3'


You can use the standard python literal syntax to set numbers, bools, lists,
dicts, strings and combinations thereof::

    >>> ./example.py with 'my_list=[1, 2, 3]'
    >>> ./example.py with 'nested_list=[["a", "b"], [2, 3], False]'
    >>> ./example.py with 'my_dict={"a":1, "b":[-.2, "two"]}'
    >>> ./example.py with 'alpha=-.3e-7'
    >>> ./example.py with 'mask=0b111000'
    >>> ./example.py with 'message="Hello Bob!"'

**Dotted Notation**

If you want to set individual entries of a dictionary you can use the dotted
notation to do so. So if this is the ConfigScope of our experiment:

.. code-block:: python

    @ex.config
    def cfg():
        d = {
            "foo": 1,
            "bar": 2,
        }

Then we could just change the ``"foo"`` entry of our dictionary to ``100`` like
this::

    >>> ./example.py with 'd.foo=100'

Named Updates
=============
If there are any :ref:`named_configurations` set up for an experiment, then you
can apply them using the ``with`` argument. So for this experiment:

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

The named configuration ``variant1`` can be applied like this::

    >>> ./named_configs_demo.py with variant1


Multiple Named Updates
----------------------
You can have multiple named configurations, and you can use as many of them
as you like for any given run. But notice that the order in which you
include them matters: The ones you put first will be evaluated first and
the values they set might be overwritten by further named configurations.

Combination With Regular Updates
--------------------------------
If you combine named updates with regular updates, and the latter have
precedence. Sacred will first set an fix all regular updates and then run
through all named updates in order, while keeping the regular updates fixed.
The resulting configuration is then kept fixed and sacred runs through all
normal configurations.

The following will set ``a=23`` first and then execute ``variant1`` treating
``a`` as fixed::

    >>> ./named_configs_demo.py with variant1 'a=23'

So this configuration becomes ``{'a':23, 'b':69, 'c':"bar"}``.

Config Files As Named Updates
-----------------------------
Config files can be used as named updates, by just passing their name to the
``with`` argument. So assuming there is a ``variant2.json`` this works::

    >>> ./named_configs_demo.py with variant2.json

Supported formats are the same as with :ref:`config_files`.

If there should ever be a name-collision between a named config and a config
file the latter takes precedence.


Print Config
============

To inspect the configuration of your experiment and see how changes from the
command-line affect it you can use the ``print_config`` command. The full
configuration of the experiment and all nested dictionaries will be printed with
indentation. So lets say we added the dictionary from above to the
``hello_config.py`` example::

    >>> ./hello_config print_config
    INFO - hello_config - Running command 'print_config'
    INFO - hello_config - Started
    Configuration (modified, added, typechanged):
      message = 'Hello world!'
      recipient = 'world'
      seed = 946502320
      d:
        bar = 2
        foo = 1
    INFO - hello_config - Completed after 0:00:00

This command is especially helpful to see how ``with config=update`` statements
affect the configuration. It will highlight modified entries in **green**, added
entries in **blue** and entries whose type has changed in **red**:

    ===========  =====
    Change       Color
    ===========  =====
    modified     blue
    added        green
    typechanged  red
    ===========  =====

But Sacred will also print warnings for all added and typechanged entries, to
help you find typos and update mistakes::

    >> ./hello_config.py print_config with 'recipient="Bob"' d.foo=True d.baz=3
    WARNING - root - Added new config entry: "d.baz"
    WARNING - root - Changed type of config entry "d.foo" from int to bool
    INFO - hello_config - Running command 'print_config'
    INFO - hello_config - Started
    Configuration (modified, added, typechanged):
      message = 'Hello Bob!'
      recipient = 'Bob'        # blue
      seed = 676870791
      d:                       # blue
        bar = 2
        baz = 3                # green
        foo = True             # red
    INFO - hello_config - Completed after 0:00:00

Custom Commands
===============
If you just run an experiment file it will execute the default command, that
is the method you decorated with ``@ex.main`` or ``@ex.automain``. But you
can also add other commands to the experiment by using ``@ex.command``:

.. code-block:: python

    from sacred import Experiment

    ex = Experiment('custom_command')

    @ex.command
    def scream():
        """
        scream, and shout, and let it all out ...
        """
        print('AAAaaaaaaaahhhhhh...')

    # ...

This command can then be run like this::

    >> ./custom_command.py scream
    INFO - custom_command - Running command 'scream'
    INFO - custom_command - Started
    AAAaaaaaaaahhhhhh...
    INFO - custom_command - Completed after 0:00:00

It will also show up in the usage message and you can get the signature and
the docstring by passing it to help::

    >> ./custom_command.py help scream

    scream()
        scream, and shout, and let it all out ...

Commands are of course also captured functions, so you can take arguments that
will get filled in from the config, and you can use ``with config=update`` to
change parameters from the command-line:

.. code-block:: python

    @ex.command
    def greet(name):
        """
        Print a simple greet message.
        """
        print('Hello %s!' % name)

And call it like this::

    >> ./custom_command.py greet with 'name="Bob"'
    INFO - custom_command - Running command 'scream'
    INFO - custom_command - Started
    Hello Bob!
    INFO - custom_command - Completed after 0:00:00

Flags
=====

**Help**

+------------+-----------------------------+
| ``-h``     |  print usage                |
+------------+                             |
| ``--help`` |                             |
+------------+-----------------------------+

This prints a help/usage message for your experiment.
It is equivalent to typing just ``help``.

**Comment**
+-----------------------+-----------------------------+
| ``-c COMMENT``        |  add a comment to this run  |
+-----------------------+                             |
| ``--comment COMMENT`` |                             |
+-----------------------+-----------------------------+

The ``COMMENT`` can be any text and will be stored with the run.

**Logging Level**

+----------------------+-----------------------------+
| ``-l LEVEL``         |  control the logging level  |
+----------------------+                             |
| ``--loglevel=LEVEL`` |                             |
+----------------------+-----------------------------+

With this flag you can adjust the logging level.

+----------+---------------+
| Level    | Numeric value |
+==========+===============+
| CRITICAL | 50            |
+----------+---------------+
| ERROR    | 40            |
+----------+---------------+
| WARNING  | 30            |
+----------+---------------+
| INFO     | 20            |
+----------+---------------+
| DEBUG    | 10            |
+----------+---------------+
| NOTSET   | 0             |
+----------+---------------+

See :ref:`log_levels` for more details.

**MongoDB Observer**

+-------------------+--------------------------+
| ``-m DB``         |  add a MongoDB observer  |
+-------------------+                          |
| ``--mongo_db=DB`` |                          |
+-------------------+--------------------------+


This flag can be used to add a MongoDB observer to your experiment. ``DB`` must
be of the form ``db_name`` or ``[host:port:]db_name``.

See :ref:`mongo_observer` for more details.

**Debug Mode**

+-------------------+-------------------------------+
| ``-d``            |  don't filter the stacktrace  |
+-------------------+                               |
| ``--debug``       |                               |
+-------------------+-------------------------------+

This flag deactivates the stacktrace filtering. You should usually not need
this. It is mainly used for debugging Sacred.

**Beat Interval**

+-----------------------------------------+-----------------------------------------------+
| ``-b BEAT_INTERVAL``                    |  set the interval between heartbeat events    |
+-----------------------------------------+                                               |
| ``--beat_interval=BEAT_INTERVAL``       |                                               |
+-----------------------------------------+-----------------------------------------------+

Custom Flags
============
It is possible to add custom flags to an experiment by inheriting from
``sacred.commandline_option.CommandLineOption`` like this:

.. code-block:: python

    from sacred.commandline_option import CommandLineOption

    class OwnFlag(CommandLineOption):
    """ This is my personal flag """

        @classmethod
        def apply(cls, args, run):
            # useless feature: add some string to the info dict
            run.info['some'] = 'prepopulation of the info dict'


The name of the flag is taken from the class name and here would be
``-o``/``-own_flag``. The short flag can be customized by setting a
``short_flag`` class variable. The documentation for the flag is taken from
the docstring. The ``apply`` method of that class is called after the ``Run``
object has been created, but before it has been started.

In this case the ``args`` parameter will be always be ``True``. But it is also
possible to add a flag which takes an argument, by specifying the ``arg``
and ``arg_description`` class variables:

.. code-block:: python

    from sacred.commandline_option import CommandLineOption

    class ImprovedFlag(CommandLineOption):
    """ This is my even better personal flag """

        short_flag = 'q'
        arg = 'MESSAGE'
        arg_description = 'The cool message that gets saved to info'

        @classmethod
        def apply(cls, args, run):
            run.info['some'] = args

Here the flag would be ``-q MESSAGE`` / ``-improved_flag=MESSAGE`` and
the ``args`` parameter of the ``apply`` function would contain the
``MESSAGE`` as a string.
