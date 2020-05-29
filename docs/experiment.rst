Experiment Overview
*******************
``Experiment`` is the central class of the Sacred framework. This section
provides an overview of what it does and how to use it.

Create an Experiment
====================
To create an ``Experiment`` just instantiate it and add main method:

.. code-block:: python

    from sacred import Experiment
    ex = Experiment()

    @ex.main
    def my_main():
        pass

The function decorated with ``@ex.main`` is the main function of the experiment.
It is executed if you run the experiment and it is also used to determine
the source-file of the experiment.

Instead of ``@ex.main`` it is recommended to use ``@ex.automain``. This will
automatically run the experiment if you execute the file. It is equivalent to
the following:

.. code-block:: python

    from sacred import Experiment
    ex = Experiment()

    @ex.main
    def my_main():
        pass

    if __name__ == '__main__':
        ex.run_commandline()

.. note::
    For this to work the ``automain`` function needs to be at the end of the
    file. Otherwise everything below it is not defined yet when the
    experiment is run.


Run the Experiment
==================
The easiest way to run your experiment is to just use the command-line. This
requires that you used ``automain`` (or an equivalent). You can then just
execute the experiments python file and use the powerful :doc:`command_line`.

You can also run your experiment directly from python. This is especially useful
if you want to run it multiple times with different configurations. So lets say
your experiment is in a file called ``my_experiment.py``. Then you can import
it from there and run it like this:

.. code-block:: python

    from my_experiment import ex

    r = ex.run()

.. warning::

    By default, Sacred experiments **will fail** if run in an interactive
    environment like a REPL or a Jupyter Notebook.
    This is an intended security measure since in these environments
    reproducibility cannot be ensured.
    If needed, this safeguard can be deactivated by passing
    ``interactive=True`` to the experiment like this:

     .. code-block:: python

        ex = Experiment('jupyter_ex', interactive=True)


The ``run`` function accepts ``config_updates`` to specify how the configuration
should be changed for this run. It should be (possibly nested) dictionary
containing all the values that you wish to update. For more information see
:doc:`configuration`:

.. code-block:: python

    from my_experiment import ex

    r = ex.run(config_updates={'foo': 23})

.. note::

    Under the hood a ``Run`` object is created every time you run an
    ``Experiment`` (this is also the object that ``ex.run()`` returns).
    It holds some information about that run (e.g. final configuration and
    later the result) and is responsible for emitting all the events for the
    :doc:`observers`.

    While the experiment is running you can access it by
    accepting the special `_run` argument in any of your
    :ref:`captured_functions`. That is also used for :ref:`custom_info`.


Configuration
=============
There are multiple ways of adding configuration to your experiment.
The easiest way is through :ref:`config_scopes`:

.. code-block:: python

    @ex.config
    def my_config():
        foo = 42
        bar = 'baz'

The local variables from that function are collected and form the configuration
of your experiment. You have full access to the power of python when defining
the configuration that way. The parameters can even depend on each other.

.. note::
    Only variables that are JSON serializable (i.e. a numbers, strings,
    lists, tuples, dictionaries) become part of the configuration. Other
    variables are ignored.

If you think that is too much magic going on, you can always use a plain
dictionary to add configuration or, if you prefer, you can also directly
load configuration entries from a file.

And of course you can combine all of them and even have several of each kind.
They will be executed in the order that you added them,
and possibly overwrite each others values.

Capture Functions
=================
To use a configuration value all you have to do is *capture* a function and
accept the configuration value as a parameter. Whenever you now call that function Sacred will
try to fill in missing parameters from the configuration.
To see how that works we need to *capture* some function:

.. code-block:: python

    from sacred import Experiment
    ex = Experiment('my_experiment')

    @ex.config
    def my_config():
        foo = 42
        bar = 'baz'

    @ex.capture
    def some_function(a, foo, bar=10):
        print(a, foo, bar)

    @ex.main
    def my_main():
        some_function(1, 2, 3)     #  1  2   3
        some_function(1)           #  1  42  'baz'
        some_function(1, bar=12)   #  1  42  12
        some_function()            #  TypeError: missing value for 'a'

More on this in the :ref:`captured_functions` Section.

.. note::
    Configuration values are preferred over default values. So in the example
    above, ``bar=10`` is never used because there is a value of ``bar = 'baz'``
    in the configuration.


Observe an Experiment
=====================
Experiments in Sacred collect lots of information about their runs like:

  - time it was started and time it stopped
  - the used configuration
  - the result or any errors that occurred
  - basic information about the machine it runs on
  - packages the experiment depends on and their versions
  - all imported local source-files
  - files opened with ``ex.open_resource``
  - files added with ``ex.add_artifact``

To access this information you can use the observer interface. First you need to
add an observer like this:

.. code-block:: python

    from sacred.observers import MongoObserver

    ex.observers.append(MongoObserver())

``MongoObserver`` is one of the default observers shipped with Sacred.
It connects to a MongoDB and puts all these information into a document in a
collection called ``experiments``. You can also add this observer from the
:doc:`command_line` like this::

    >> python my_experiment.py -m my_database

For more information see :doc:`observers`

.. _capturing:

Capturing stdout / stderr
-------------------------
Sacred tries to capture all outputs and transmits that information to the
observers. This behaviour is configurable and can happen in three different
modes: ``no``, ``sys`` and ``fd``. This mode can be
:ref:`set from the commandline <cmdline_capture>` or in the :ref:`settings`.

In the ``no`` mode none of the outputs are captured. This is the default
behaviour if no observers are added to the experiment.

If the capture mode is set to ``sys`` then sacred captures all outputs written
to ``sys.stdout`` and ``sys.stderr`` such as ``print`` statements, stacktraces
and logging. In this mode outputs by system-calls, C-extensions or subprocesses
are likely *not captured*. This behaviour is default for Windows.

Finally, the ``fd`` mode captures outputs on the file descriptor level, and
should include all outputs made by the program or any child-processes.
This is the default behaviour for Linux and OSX.

The captured output contains all printed characters and behaves like a file
and not like a terminal. Sometimes this is unwanted, for example when the
output contains lots of live-updates like progressbars.
To prevent the captured out from retaining each and every update that is
written to the console one can add a *captured out filter* to the experiment
like this:

.. code-block:: python

    from sacred.utils import apply_backspaces_and_linefeeds

    ex.captured_out_filter = apply_backspaces_and_linefeeds

Here ``apply_backspaces_and_linefeeds`` is a simple function that interprets
all backspace and linefeed characters like in a terminal and returns the
modified text.
Any function that takes a string as input and outputs a (modified) string can
be used as a ``captured_out_filter``.
For a simple example see `examples/captured_out_filter.py <https://github.com/IDSIA/sacred/tree/master/examples/captured_out_filter.py>`_.


Interrupted and Failed Experiments
==================================
If a run is interrupted (e.g. Ctrl+C) or if an exception occurs, Sacred will
gather the stacktrace and the fail time and report them to the observers.
The resulting entries will have their status set to ``INTERRUPTED`` or to
``FAILED``. This allows to quickly see the reason for a non-successful run, and
enables later investigation of the errors.

Detecting Hard Failures
-----------------------
Sometimes an experiment can fail without an exception being thrown
(e.g. power loss, kernel panic, ...). In that case the failure cannot be logged
to the database and their status will still be ``RUNNING``.
Runs that fail in that way are most easily detected by investigating their
heartbeat time: each running experiment reports to its observers in regular
intervals (default every 10 sec) and updates the heartbeat time along with the
captured stdout and the info dict (see :ref:`custom_info`). So if the heartbeat
time lies much further back in time than that interval, the run can be
considered dead.

.. _debugging:

Debugging
---------
If an Exception occurs, sacred by default filters the stacktrace by removing
all sacred-internal calls. The stacktrace is of course also saved in the
database (if appropriate observer is added).
This helps to quickly spot errors in your own code.
However, if you want to use a debugger, stacktrace filtering needs to be
disabled, because it doesn't play well with debuggers like ``pdb``.

If you want to use a debugger with your experiment, you have two options:

Disable Stacktrace Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Stacktrace filtering can be deactivated via the ``-d`` flag.
Sacred then does not interfere with the exception and it can be properly
handled by any debugger.

Post-Mortem Debugging
~~~~~~~~~~~~~~~~~~~~~
For convenience Sacred also supports directly attaching a post-mortem ``pdb``
debugger via the ``-D`` flag.
If this option is set and an exception occurs, sacred will automatically start
``pdb`` debugger to investigate the error, and interact with the stack.

.. _custom_interrupts:

Custom Interrupts
-----------------
Sometimes it can be useful to have custom reasons for interrupting an
experiment. One example is if there is a limited time budget for an experiment.
If the experiment is stopped because of exceeding that limit, that should be
reflected in the database entries.

For these cases, Sacred offers a special base exception
:py:class:`sacred.utils.SacredInterrupt` that can be used to provide a custom
status code. If an exception derived from this one is raised, then the
status of the interrupted run will be set to that code.

For the aforementioned timeout usecase there is the
:py:class:`sacred.utils.TimeoutInterrupt` exception with the status code
``TIMEOUT``.
But any status code can be used by simply creating a custom exception that
inherits from :py:class:`sacred.utils.SacredInterrupt` and defines a ``STATUS``
member like this:

.. code-block:: python

    from sacred.utils import SacredInterrupt

    class CustomInterrupt(SacredInterrupt)
        STATUS = 'MY_CUSTOM_STATUS'


When this exception is raised during any run, its status is set to
``MY_CUSTOM_STATUS``.


.. _queuing:

Queuing a Run
=============
Sacred also supports queuing runs by passing the :ref:`cmdline_queue` flag
(``-q``/``--queue``). This will **not** run the experiment, but instead only
create a database entry that holds all information needed to start the run.
This feature could be useful for having a distributed pool of workers that get
configurations from the database and run them. As of yet, however, there is
no further support for this workflow.
