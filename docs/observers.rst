Observing an Experiment
***********************
When you run an experiment you want to keep track of enough information,
such that you can analyse the results, and reproduce them if needed.
Sacred helps you doing that by providing an *Observer Interface* for your
experiments. By attaching an Observer you can gather all the information about
the run even while it is still running.

.. _mongo_observer:

The MongoDB Observer
====================
The easiest way to use that is to use the included MongoObserver.
You can add that via the commandline by adding the ``-m MY_DB`` flag. This will
gather all the information and save it to MY_DB in your local MongoDB.

This assumes you have a local `MongoDB <http://www.mongodb.org/>`_ running. See
`here <http://docs.mongodb.org/manual/installation/>`_ on how to install.

You can also add it from code like this:

.. code-block:: python

    from sacred.observers import MongoObserver

    ex.observers.append(MongoObserver())

To make MongoObserver work with remote MongoDBs you have to pass a URL with a port::

    >> ./my_experiment.py -m HOST:PORT:MY_DB
    >> ./my_experiment.py -m 192.168.1.1:27017:MY_DB
    >> ./my_experiment.py -m my.server.org:12345:MY_DB

Or in code:

.. code-block:: python

    from sacred.observers import MongoObserver

    ex.observers.append(MongoObserver(url='my.server.org:27017', db_name='MY_DB'))

For each run of the experiment this will generate a document in the database
with lots of information about that run.

What Is Being Observed
======================
An event is fired when a run starts, every 10 seconds while the experiment is
running and one, once it stops (either successfully or not).

Start
-----
The moment an experiment is started, the first event is fired for all the
observers. It contains the following information:

    ===========  ===============================================================
    name         The name of the experiment
    config       The configuration for this run, including the root-seed.
    start_time   The date/time it was started
    ex_info      Some information about the experiment:

                    * filename of the source-file of the experiment
                    * the docstring of the experiment-file
                    * dictionary of packages the experiment depends on and their used versions

    host_info    Some information about the machine it's being run on:

                    * CPU name
                    * number of CPUs
                    * hostname
                    * Operating System
                    * Python version
                    * Python compiler
    ===========  ===============================================================


Heartbeat
---------
While the experiment is running, every 10 seconds a Heartbeat event is fired.
It updates the **captured stdout and stderr** of the experiment and the custom
``info`` (see below). The heartbeat event is also a way of monitoring if an
experiment is still running.


Stop
----
Sacred distinguishes three ways in which an experiment can end:

Successful Completion:
    If an experiment finishes without an error, a ``completed_event`` is fired,
    which contains the time it completed and the result the command returned.

Interrupted:
    If a ``KeyboardInterrupt`` exception occurs (most of time this means you
    cancelled the experiment manually) instead an ``interrupted_event`` is fired,
    which only contains the interrupt time.

Failed:
    In case any other exception occurs, Sacred fires a ``failed_event`` with the
    fail time and the corresponding stacktrace.

Saving Custom Information
=========================
Sometimes you want to add custom information about the run of an experiment,
like the error curves during training. The easiest way of doing that is by using
the special ``_run`` parameter in any captured function. This gives you access
to the current ``Run`` object. You can then just add whatever information you
like to ``_run.info``. This ``info`` dict will be sent to all the observers
every 10 sec as part of the heartbeat_event.

.. note::
    It is recommended to only store information in ``info`` that is
    JSON-serializable and contains only valid python identifiers as keys in
    dictionaries. That way you make sure that it can be saved to the database by
    the MongoObserver.
