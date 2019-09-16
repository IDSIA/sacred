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

.. note::
    Note however, that changing individual elements of a list is not supported now.

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

Commands
========

Apart from running the main function (the default command), the command-line
interface also supports other (built-in or custom) commands.
The name of the command has to be first on the commandline::

    >>> ./my_demo.py COMMAND_NAME with seed=123

If the COMMAND_NAME is omitted it defaults to the main function, but the name
of that function can also explicitly used as the name of the command.
So for this experiment

.. code-block:: python

    @ex.automain
    def my_main():
        return 42

the following two lines are equivalent::

    >>> ./my_demo.py with seed=123
    >>> ./my_demo.py my_main with seed=123

.. _print_config:

Print Config
------------

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


.. _print_dependencies:

Print Dependencies
------------------

The ``print_dependencies`` command shows the package dependencies, source files,
and (optionally) the state of version control for the experiment. For example::

    >> ./03_hello_config_scope.py print_dependencies
    INFO - hello_cs - Running command 'print_dependencies'
    INFO - hello_cs - Started
    Dependencies:
      numpy                == 1.11.0
      sacred               == 0.7.0

    Sources:
      03_hello_config_scope.py                     53cee32c9dc77870f7b39622434aff85

    Version Control:
    M git@github.com:IDSIA/sacred.git              bcdde712957570606ec5087b1748c60a89bb89e0

    INFO - hello_cs - Completed after 0:00:00

Where the *Sources* section lists all discovered (or added) source files and their
md5 hash.
The *Version Control* section lists all discovered VCS repositories
(ATM only git is supported), the current commit hash.
The M at the beginning of the git line signals that the repository is currently
dirty, i.e. has uncommitted changes.


.. _save_config:

Save Configuration
------------------

Use the ``save_config`` command for saving the current/updated configuration
into a file::

    ./03_hello_config_scope.py save_config with recipient=Bob

This will store a file called ``config.json`` with the following content::

    {
      "message": "Hello Bob!",
      "recipient": "Bob",
      "seed": 151625947
    }

The filename can be configured by setting ``config_filename`` like this::

    ./03_hello_config_scope.py save_config with recipient=Bob config_filename=mine.yaml

The format for exporting the config is inferred from the filename and can be
any format supported for :ref:`config files <config_files>`.


.. _print_named_configs:

Print Named Configs
-------------------

The ``print_named_configs`` command prints all available named configurations.
Function docstrings for named config functions are copied and displayed colored
in **grey**.
For example::

    >> ./named_config print_named_configs
    INFO - hello_config - Running command 'print_named_configs'
    INFO - hello_config - Started
    Named Configurations (doc):
      rude   # A rude named config
    INFO - hello_config - Completed after 0:00:00

If no named configs are available for the experiment, an empty list is printed::

    >> ./01_hello_world print_named_configs
    INFO - 01_hello_world - Running command 'print_named_configs'
    INFO - 01_hello_world - Started
    Named Configurations (doc):
      No named configs
    INFO - 01_hello_world - Completed after 0:00:00

Custom Commands
---------------
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

Like other :ref:`captured_functions`, commands also accept the ``prefix``
keyword-argument.

Many commands like ``print_config`` are helper functions, and should not
trigger observers. This can be accomplished by passing ``unobserved=True`` to
the decorator:

.. code-block:: python

    @ex.command(unobserved=True)
    def helper(name):
        print('Running this command will not result in a DB entry!')


Flags
=====

Help
----

+------------+-----------------------------+
| ``-h``     |  print usage                |
+------------+                             |
| ``--help`` |                             |
+------------+-----------------------------+

This prints a help/usage message for your experiment.
It is equivalent to typing just ``help``.

.. _comment_flag:

Comment
-------

+-----------------------+-----------------------------+
| ``-c COMMENT``        |  add a comment to this run  |
+-----------------------+                             |
| ``--comment COMMENT`` |                             |
+-----------------------+-----------------------------+

The ``COMMENT`` can be any text and will be stored with the run.

Logging Level
-------------

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

MongoDB Observer
----------------

+-------------------+--------------------------+
| ``-m DB``         |  add a MongoDB observer  |
+-------------------+                          |
| ``--mongo_db=DB`` |                          |
+-------------------+--------------------------+


This flag can be used to add a MongoDB observer to your experiment. ``DB`` must
be of the form ``[host:port:]db_name[.collection][!priority]``.

See :ref:`mongo_observer` for more details.


FileStorage Observer
--------------------

+----------------------------+------------------------------+
| ``-F BASEDIR``             |  add a file storage observer |
+----------------------------+                              |
| ``--file_storage=BASEDIR`` |                              |
+----------------------------+------------------------------+


This flag can be used to add a file-storage observer to your experiment.
``BASEDIR`` specifies the directory the observer will use to store its files.

See :ref:`file_observer` for more details.


TinyDB Observer
---------------

+-----------------------+------------------------------+
| ``-t BASEDIR``        |  add a TinyDB observer       |
+-----------------------+                              |
| ``--tiny_db=BASEDIR`` |                              |
+-----------------------+------------------------------+


This flag can be used to add a TinyDB observer to your experiment.
``BASEDIR`` specifies the directory the observer will use to store its files.

See :ref:`tinydb_observer` for more details.

.. note::
    For this flag to work you need to have the
    `tinydb <http://tinydb.readthedocs.io>`_,
    `tinydb-serialization <https://github.com/msiemens/tinydb-serialization>`_,
    and `hashfs <https://github.com/dgilland/hashfs>`_ packages installed.


SQL Observer
------------

+------------------+--------------------------+
| ``-s DB_URL``    |  add a SQL observer      |
+------------------+                          |
| ``--sql=DB_URL`` |                          |
+------------------+--------------------------+


This flag can be used to add a SQL observer to your experiment.
``DB_URL`` must be parseable by the `sqlalchemy <http://www.sqlalchemy.org/>`_
package, which is typically means being of the form
``dialect://username:password@host:port/database`` (see their
`documentation <http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>`_
for more detail).

.. note::
    For this flag to work you need to have the
    `sqlalchemy <http://www.sqlalchemy.org/>`_ package installed.

See :ref:`mongo_observer` for more details.


Debug Mode
----------

+-------------------+-------------------------------+
| ``-d``            |  don't filter the stacktrace  |
+-------------------+                               |
| ``--debug``       |                               |
+-------------------+-------------------------------+

This flag deactivates the stacktrace filtering. You should usually not need
this. It is mainly used for debugging experiments using a debugger
(see :ref:`debugging`).


PDB Debugging
-------------

+-------------------+----------------------------------------------------+
| ``-D``            |  Enter post-mortem debugging with pdb on failure.  |
+-------------------+                                                    |
| ``--pdb``         |                                                    |
+-------------------+----------------------------------------------------+

If this flag is set and an exception occurs, sacred automatically starts a
``pdb`` post-mortem debugger to investigate the error and interact with the
stack (see :ref:`debugging`).

Beat Interval
-------------

+-----------------------------------------+-----------------------------------------------+
| ``-b BEAT_INTERVAL``                    |  set the interval between heartbeat events    |
+-----------------------------------------+                                               |
| ``--beat_interval=BEAT_INTERVAL``       |                                               |
+-----------------------------------------+-----------------------------------------------+

A running experiment regularly fires a :ref:`heartbeat` event to synchronize
the ``info`` dict (see :ref:`custom_info`).
This flag can be used to change the interval from 10 sec (default) to
``BEAT_INTERVAL`` sec.


Unobserved
----------

+------------------+--------------------------------------+
| ``-u``           |  Ignore all observers for this run.  |
+------------------+                                      |
| ``--unobserved`` |                                      |
+------------------+--------------------------------------+

If this flag is set, sacred will remove all observers from the current run and
also silence the warning for having no observers. This is useful for some quick
tests or debugging runs.


.. _cmdline_queue:

Queue
-----

+---------------+-----------------------------------------+
| ``-q``        |  Only queue this run, do not start it.  |
+---------------+                                         |
| ``--queue``   |                                         |
+---------------+-----------------------------------------+

Instead of running the experiment, this will only create an entry in the
database (or where the observers put it) with the status ``QUEUED``.
This entry will contain all the information about the experiment and the
configuration. But the experiment will not be run. This can be useful to have
some distributed workers fetch and start the queued up runs.

.. _cmdline_priority:

Priority
--------

+--------------------------+----------------------------------------+
| ``-P PRIORITY``          |  The (numeric) priority for this run.  |
+--------------------------+                                        |
| ``--priority=PRIORITY``  |                                        |
+--------------------------+----------------------------------------+



.. _cmdline_enforce_clean:

Enforce Clean
-------------
+---------------------+----------------------------------------------------+
| ``-e``              |  Fail if any version control repository is dirty.  |
+---------------------+                                                    |
| ``--enforce_clean`` |                                                    |
+---------------------+----------------------------------------------------+

This flag can be used to enforce that experiments are only being run on a clean
repository, i.e. with no uncommitted changes.

.. note::
    For this flag to work you need to have the
    `GitPython <https://github.com/gitpython-developers/GitPython>`_
    package installed.


.. _cmdline_print_config:

Print Config
------------
+------------------------+------------------------------------------+
| ``-p``                 |  Always print the config first.          |
+------------------------+                                          |
| ``--print_config``     |                                          |
+------------------------+------------------------------------------+

If this flag is set, sacred will always print the current configuration
including modifications (like the :ref:`print_config` command) before running
the main method.


Name
----
+-----------------+---------------------------------------------------+
| ``-n NAME``     |  Set the name for this run.                       |
+-----------------+                                                   |
| ``--name=NAME`` |                                                   |
+-----------------+---------------------------------------------------+

This option changes the name of the experiment before starting the run.

.. _cmdline_capture:

Capture Mode
------------
+----------------------------+------------------------------------------------------+
| ``-C CAPTURE_MODE``        |  Control the way stdout and stderr are captured.     |
+----------------------------+                                                      |
| ``--capture=CAPTURE_MODE`` |                                                      |
+----------------------------+------------------------------------------------------+

This option controls how sacred captures outputs to stdout and stderr.
Possible values for ``CAPTURE_MODE`` are ``no``, ``sys`` (default under Windows),
or ``fd`` (default for Linux/OSX). For more information see :ref:`here <capturing>`.



Custom Flags
============
It is possible to add custom flags to an experiment by inheriting from
``sacred.cli_option`` like this:

.. code-block:: python

    from sacred import cli_option, Experiment


    @cli_option('-o', '--own-flag', is_flag=True)
    def my_option(args, run):
        # useless feature: add some string to the info dict
        run.info['some'] = 'prepopulation of the info dict'


    ex = Experiment('my pretty exp', additional_cli_options=[my_option])

    @ex.run
    def my_main():
        ...


The name of the flag is taken from the decorator arguments and here would be
``-o``/``--own-flag``. The documentation for the flag is taken from
the docstring. The decorated function is called after the ``Run``
object has been created, but before it has been started.

In this case the ``args`` parameter will be always be ``True``. But it is also
possible to add a flag which takes an argument, by turning off
the ``is_flag`` option (which is the default):

.. code-block:: python

    from sacred import cli_option, Experiment


    @cli_option('-o', '--own-flag')  # is_flag=False is the default
    def improved_option(args, run):
        """
        This is my even better personal flag
        The cool message that gets saved to info.
        """
        run.info['some'] = args


    ex = Experiment('my pretty exp', additional_cli_options=[improved_option])

    @ex.run
    def my_main():
        ...

Here the flag would be ``-o MESSAGE`` / ``--own-flag=MESSAGE`` and
the ``args`` parameter of the ``apply`` function would contain the
``MESSAGE`` as a string.
