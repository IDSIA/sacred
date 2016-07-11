Observing an Experiment
***********************
When you run an experiment you want to keep track of enough information,
such that you can analyse the results, and reproduce them if needed.
Sacred helps you doing that by providing an *Observer Interface* for your
experiments. By attaching an Observer you can gather all the information about
the run even while it is still running.

At the moment there are three observers that are shipped with Sacred:

 * The main one is the :ref:`mongo_observer` which stores all information in a
   `MongoDB <http://www.mongodb.org/>`_.
 * The :ref:`file_observer` stores the run information as files in a given
   directory and will therefore only work locally.
 * The :ref:`sql_observer` connects to any SQL database and will store the
   relevant information there.

But if you want the run information stored some other way, it is easy to write
your own :ref:`custom_observer`.

.. _mongo_observer:

MongoObserver
=============
The MongoObserver is the recommended way of storing the run information from
Sacred.
MongoDB allows very powerful querying of the entries that can deal with
almost any structure of the configuration and the custom info.
Furthermore it is easy to set-up and allows to connect to a central remote DB.
Most tools for further analysing the data collected by Sacred build upon this
observer.

Adding a MongoObserver
----------------------
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
--------------
The MongoObserver creates three collections to store information. The first,
``runs`` (that name can be changed), is the main collection that contains one
entry for each run.
The other two (``fs.files``, ``fs.chunks``) are used to store associated files
in the database (compare `GridFS <http://docs.mongodb.org/manual/core/gridfs/>`_).

.. note::
    This is the new database layout introduced in version 0.7.0.
    Before that there was a common prefix `default` for all collections.

So here is an example entry in the ``runs`` collection::

    > db.runs.find()[0]
    {
        "_id" : ObjectId("5507248a1239672ae04591e2"),
        "format" : "MongoObserver-0.7.0",
        "status" : "COMPLETED",
        "result" : null,
        "start_time" : ISODate("2016-07-11T14:50:14.473Z"),
        "heartbeat" : ISODate("2015-03-16T19:44:26.530Z"),
        "stop_time" : ISODate("2015-03-16T19:44:26.532Z"),
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
            "name" : "hello_cs",
            "base_dir" : "$(HOME)/sacred/examples/"
            "dependencies" : ["numpy==1.9.1", "sacred==0.7.0"],
            "sources" : [
                [
                    "03_hello_config_scope.py",
                    ObjectId("5507248a1239672ae04591e3")
                ]
            ],
            "repositories" : [{
                "url" : "git@github.com:IDSIA/sacred.git"
				"dirty" : false,
				"commit" : "d88deb2555bb311eb779f81f22fe16dd3b703527"}]
        },
        "host" : {
            "os" : ["Linux",
                    "Linux-3.13.0-46-generic-x86_64-with-Ubuntu-14.04-trusty"],
            "cpu" : "Intel(R) Core(TM) i7-3770 CPU @ 3.40GHz",
            "hostname" : "MyAwesomeMachine",
            "python_version" : "3.4.0"
        },
    }

As you can see a lot of relevant information is being stored, among it the
used configuration, automatically detected package dependencies and information
about the host.

If we take a look at the ``fs.files`` collection we can also see, that
it stored the sourcecode of the experiment in the database::

    > db.fs.files.find()[0]
    {
        "_id" : ObjectId("5507248a1239672ae04591e3"),
        "filename" : "$(HOME)/sacred/examples/03_hello_config_scope.py",
        "md5" : "897b2144880e2ee8e34775929943f496",
        "chunkSize" : 261120,
        "length" : 1526,
        "uploadDate" : ISODate("2016-07-11T12:50:14.522Z")
    }


.. _file_observer:

FileStorageObserver
===================
The FileStorageObserver is the most basic observer and requires the least
amount of setup.
It is mostly meant for preliminary experiments and cases when setting up a
database is difficult or impossible.
But in combination with the template rendering integration it can be very
helpful.

Adding a FileStorageObserver
----------------------------
The FileStorageObserver can be added from the command-line via the
``-F BASEDIR`` and  ``--file_storage=BASEDIR`` flags::

    >> ./my_experiment.py -F BASEDIR
    >> ./my_experiment.py --file_storage=BASEDIR

Here ``BASEDIR`` is the name of the directory in which all the subdirectories
for individual runs will be created.

You can, of course, also add it from code like this:

.. code-block:: python

    from sacred.observers import FileStorageObserver

    ex.observers.append(FileStorageObserver.create('my_runs'))


Directory Structure
-------------------
The FileStorageObserver creates a separate sub-directory for each run and stores
several files in there::

    my_runs/
        run_3mdq4amp/
            config.json
            cout.txt
            info.json
            run.json
        run_zw82a7xg/
            ...
        ...

``config.json`` contains the JSON-serialized version of the configuration
and ``cout.txt`` the captured output.
The main information is stored in ``run.json`` and is very similar to the
database entries from the :ref:`mongo_observer`::

    {
      "command": "main",
      "status": "COMPLETED",
      "start_time": "2016-07-11T15:35:14.765152",
      "heartbeat": "2016-07-11T15:35:14.766793",
      "stop_time": "2016-07-11T15:35:14.768465",
      "result": null,
      "experiment": {
        "base_dir": "/home/greff/Programming/sacred/examples",
        "dependencies": [
          "numpy==1.11.0",
          "sacred==0.6.9"],
        "name": "hello_cs",
        "repositories": [{
            "commit": "d88deb2555bb311eb779f81f22fe16dd3b703527",
            "dirty": false,
            "url": "git@github.com:IDSIA/sacred.git"}],
        "sources": [
          ["03_hello_config_scope.py",
           "_sources/03_hello_config_scope_897b2144880e2ee8e34775929943f496.py"]]
      },
      "host": {
        "cpu": "Intel(R) Core(TM) i7-3770 CPU @ 3.40GHz",
        "hostname": "Liz",
        "os": ["Linux",
               "Linux-3.19.0-58-generic-x86_64-with-Ubuntu-15.04-vivid"],
        "python_version": "3.4.3"
      },
      "artifacts": [],
      "resources": [],
      "meta": {},
    }

In addition to that there is an ``info.json`` file holding :ref:`custom_info`
(if existing) and all the :ref:`artifacts`.

The FileStorageObserver also stores a snapshot of the source-code in a separate
``my_runs/_sources`` directory, and :ref:`resources` in ``my_runs/_resources``
(if present).
Their filenames are stored in the ``run.json`` file such that the corresponding
files can be easily linked to their respective run.

Template Rendering
------------------
In addition to these basic files, the FileStorageObserver can also generate a
report for each run from a given template file.
The prerequisite for this is that the `mako <http://www.makotemplates.org/>`_ package is installed and a
``my_runs/template.html`` file needs to exist.
The file can be located somewhere else, but then the filename must be passed to
the FileStorageObserver like this:

.. code-block:: python

    from sacred.observers import FileStorageObserver

    ex.observers.append(FileStorageObserver.create('my_runs', template='/custom/template.txt'))

The FileStorageObserver will then render that template into a
``report.html``/``report.txt`` file in the respective run directory.
``mako`` is a very powerful templating engine that can execute
arbitrary python-code, so be careful about the templates you use.
For an example see ``sacred/examples/my_runs/template.html``.

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
    ex_info      Some information about the experiment:

                    * the docstring of the experiment-file
                    * filename and md5 hash for all source-dependencies of the experiment
                    * names and versions of packages the experiment depends on
    command      The name of the command that was run.
    host_info    Some information about the machine it's being run on:

                    * CPU name
                    * number of CPUs
                    * hostname
                    * Operating System
                    * Python version
                    * Python compiler
    start_time   The date/time it was started
    config       The configuration for this run, including the root-seed.
    meta_info    Meta-information about this run such as a custom comment
                 and the priority of this run.
    _id          The ID of this run, as determined by the first observer
    ===========  ===============================================================

The started event is also the time when the ID of the run is determined.
Essentially the first observer which sees `_id=None` sets an id and returns it.
That id is then stored in the run and also passed to all further observers.

.. _heartbeat:

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
with that filename (see :ref:`resources`).

Artifacts
---------
Every time ``ex.add_artifact(filename)`` is called an event will be fired
with that filename (see :ref:`artifacts`).


.. _custom_info:

Saving Custom Information
=========================
Sometimes you want to add custom information about the run of an experiment,
like the dataset, error curves during training, or the final trained model.
To allow this sacred offers three different mechanisms.

Info Dict
---------
The ``info`` dictionary is meant to store small amounts of information about
the experiment, like training loss for each epoch or the total number of
parameters. It is updated on each heartbeat, such that its content is
accessible in the database already during runtime.

To store information in the ``info`` dict it can be accessed via ``ex.info``,
but only while the experiment is *running*.
Another way is to access it directly through the run with ``_run.info``.
This can be done conveniently using the special ``_run`` parameter in any
captured function, which gives you access to the current ``Run`` object.

You can add whatever information you like to ``_run.info``. This ``info`` dict
will be sent to all the observers every 10 sec as part of the heartbeat_event.

.. warning::
    You can only store information in ``info`` that is JSON-serializable and
    contains only valid python identifiers as keys in dictionaries. Otherwise
    the Observer might not be able to store it in the Database and crash.
    ``numpy`` arrays and ``pandas`` datastructures are an exception to that
    rule as they converted automatically (see below).

If the info dict contains ``numpy`` arrays or ``pandas`` Series/DataFrame/Panel
then these will be converted to json automatically. The result is human
readable (nested lists for ``numpy`` and a dict for ``pandas``). Note that this
process looses information about the precise datatypes
(e.g. uint8 will be just int afterwards).


.. _resources:

Resources
---------
Generally speaking a resource is a file that your experiment needs to read
during a run. When you open a file using  ``ex.open_resource(filename)`` then
a ``resource_event`` will be fired and the MongoObserver will check whether
that file is in the database already. If not it will store it there.
In any case the filename along with its MD5 hash is logged.

.. _artifacts:

Artifacts
---------
An artifact is a file created during the run. This mechanism is meant to store
big custom chunks of data like a trained model. With
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

