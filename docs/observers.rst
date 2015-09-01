Observing an Experiment
***********************
When you run an experiment you want to keep track of enough information,
such that you can analyse the results, and reproduce them if needed.
Sacred helps you doing that by providing an *Observer Interface* for your
experiments. By attaching an Observer you can gather all the information about
the run even while it is still running.

The only observer that is shipped with Sacred at this point is
:ref:`mongo_observer`, so we'll focus on that.
The ``MongoObserver`` collects information about an experiment and stores them
in a `MongoDB <http://www.mongodb.org/>`_.

But if you want your run infos stored some other way, it is easy to write
your own :ref:`custom_observer`.

.. _mongo_observer:

Adding a MongoObserver
======================
You can add a MongoObserver from the command-line via the ``-m MY_DB`` flag::

    >> ./my_experiment.py -m MY_DB

Here ``MY_DB`` is just the name of the database inside MongoDB that you want
the information to be stored in.
To make MongoObserver work with remote MongoDBs you have to pass a URL with a
port::

    >> ./my_experiment.py -m HOST:PORT:MY_DB
    >> ./my_experiment.py -m 192.168.1.1:27017:MY_DB
    >> ./my_experiment.py -m my.server.org:12345:MY_DB

You can also add it from code like this:

.. code-block:: python

    from sacred.observers import MongoObserver

    ex.observers.append(MongoObserver.create())



Or with server and port:

.. code-block:: python

    from sacred.observers import MongoObserver

    ex.observers.append(MongoObserver.create(url='my.server.org:27017',
                                             db_name='MY_DB'))

This assumes you either have a local MongoDB running or have access to it over
network without authentication.
(See `here <http://docs.mongodb.org/manual/installation/>`_ on how to install)

Authentication
--------------

If you need authentication a little more work might be necessary.
First you have to decide which
`authentication protocol <http://api.mongodb.org/python/current/examples/authentication.html>`_
you want to use. If it can be done by just using the ``MongoDB URI`` then just pass that, e.g.:

.. code-block:: python

    from sacred.observers import MongoObserver

    ex.observers.append(MongoObserver.create(
        url='mongodb://user:password@example.com/the_database?authMechanism=SCRAM-SHA-1',
        db_name='MY_DB'))


If additional arguments need to be passed to the MongoClient they can just be included:


.. code-block:: python

    ex.observers.append(MongoObserver.create(
        url="mongodb://<X.509 derived username>@example.com/?authMechanism=MONGODB-X509",
        db_name='MY_DB',
        ssl=True,
        ssl_certfile='/path/to/client.pem',
        ssl_cert_reqs=ssl.CERT_REQUIRED,
        ssl_ca_certs='/path/to/ca.pem'))

Database Entry
==============
The MongoObserver creates three collections with a common prefix
(default is ``default`` but can be changed) to store information. The first,
``default.runs``, is the main collection that contains one entry for each run.
The other two (``default.files``, ``default.chunks``) are used to store
associated files in the database (compare
`GridFS <http://docs.mongodb.org/manual/core/gridfs/>`_).

So here is an example entry in the ``default.runs`` collection::

    > db.default.runs.find()[0]
    {
        "_id" : ObjectId("5507248a1239672ae04591e2"),
        "status" : "COMPLETED",
        "result" : null,
        "start_time" : ISODate("2015-03-16T19:44:26.439Z"),
        "heartbeat" : ISODate("2015-03-16T19:44:26.446Z"),
        "stop_time" : ISODate("2015-03-16T19:44:26.447Z")

        "config" : {
            "message" : "Hello world!",
            "seed" : 909032414,
            "recipient" : "world"
        },
        "info" : { },
        "resources" : [ ],
        "artifacts" : [ ],
        "captured_out" : "Hello world!\n",

        "experiment" : {
            "name" : "hello_config_scope",
            "dependencies" : [
                ["numpy", "1.9.1"],
                ["sacred", "0.6"]
            ],
            "sources" : [
                [
                    "$(HOME)/sacred/examples/03_hello_config_scope.py",
                    "da6a2d6e03d122b3abead21b0c621ba9"
                ]
            ],
            "doc" : "A configurable Hello World \"experiment\".\nIn this [...]"
        },

        "host" : {
            "os" : "Linux",
            "cpu" : "Intel(R) Core(TM) i7-3770 CPU @ 3.40GHz",
            "hostname" : "MyAwesomeMachine",
            "python_version" : "3.4.0",
            "python_compiler" : "GCC 4.8.2",
            "os_info" : "Linux-3.13.0-46-generic-x86_64-with-Ubuntu-14.04-trusty",
            "cpu_count" : 8
        },
    }

As you can see a lot of relevant information is being stored, among it the
used configuration, automatically detected package dependencies and information
about the host.

If we take a look at the ``default.files`` collection we can also see, that
it stored the sourcecode of the experiment in the database::

    > db.default.files.find()[0]
    {
        "_id" : ObjectId("5507248a1239672ae04591e3"),
        "filename" : "$(HOME)/sacred/examples/03_hello_config_scope.py",
        "md5" : "da6a2d6e03d122b3abead21b0c621ba9",
        "chunkSize" : 261120,
        "length" : 1526,
        "uploadDate" : ISODate("2015-03-16T18:44:26.444Z")
    }


Events
======
A ``started_event`` is fired when a run starts.
Then every 10 seconds while the experiment is running a ``heatbeat_event`` is
fired.
Whenever a resource or artifact is added to the running experiment a
``resource_event`` resp. ``artifact_event`` is fired.
Finally, once it stops one of the three ``completed_event``,
``interrupted_event``, or ``failed_event`` is fired.


Start
-----
The moment an experiment is started, the first event is fired for all the
observers. It contains the following information:

    ===========  ===============================================================
    name         The name of the experiment
    config       The configuration for this run, including the root-seed.
    start_time   The date/time it was started
    ex_info      Some information about the experiment:

                    * the docstring of the experiment-file
                    * filename and md5 hash for all source-dependencies of the experiment
                    * names and versions of packages the experiment depends on

    host_info    Some information about the machine it's being run on:

                    * CPU name
                    * number of CPUs
                    * hostname
                    * Operating System
                    * Python version
                    * Python compiler

    comment      A custom comment given for this run
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


Resources
---------
Every time ``ex.open_resource(filename)`` is called an event will be fired
with that filename.

Artifacts
---------
Every time ``ex.add_artifact(filename)`` is called an event will be fired
with that filename.


.. _custom_info:

Saving Custom Information
=========================
Sometimes you want to add custom information about the run of an experiment,
like the error curves during training. That's what the ``info`` dictionary is
for. While the experiment is *running* it can be accessed via ``ex.info``.
Another way is by ``_run.info`` using the special ``_run`` parameter in any
captured function, which gives you access to the current ``Run`` object.

You can add whatever information you like to ``_run.info``. This ``info`` dict
will be sent to all the observers every 10 sec as part of the heartbeat_event.

.. warning::
    Note that it is recommended to only store information in ``info`` that is
    JSON-serializable and contains only valid python identifiers as keys in
    dictionaries. Otherwise the Observer might not be able to store it in the
    Database and crash.

Another way of having information saved to the database is by adding
*resources* or *artifacts*.

Resources
---------
Generally speaking a resource is a file that your experiment needs to read
during a run. When you open a file using  ``ex.open_resource(filename)`` then
a ``resource_event`` will be fired and the MongoObserver will check whether
that file is in the database already. If not it will store it there.
In any case the filename along with its MD5 hash is logged.

Artifacts
---------
An artifact is a file created during the run. With
``ex.add_artifact(filename)`` such a file can be added, which will fire an
``artifact_event``. The MongoObserver will then in turn again, store that file
in the database and log it in the run entry.


.. _custom_observer:

Custom Observer
===============

The easiest way to implement a custom observer is to inherit from
``sacred.observers.RunObserver`` and override some or all of the events:

.. code-block:: python

    from sacred.observer import RunObserver

    class MyObserver(RunObserver):
        def started_event(self, ex_info, host_info, start_time, config, comment):
            pass

        def heartbeat_event(self, info, captured_out, beat_time):
            pass

        def completed_event(self, stop_time, result):
            pass

        def interrupted_event(self, interrupt_time):
            pass

        def failed_event(self, fail_time, fail_trace):
            pass

        def resource_event(self, filename):
            pass

        def artifact_event(self, filename):
            pass

