Collected Information
*********************

Sacred collects a lot of information about the runs of an experiment and
reports them to the observers.
This section provides an overview over the collected information and ways to
customize it.

Configuration
=============
Arguably the most important information about a run is its :ref:`configuration`.
Sacred collects the final configuration that results after incorporating
named configs and configuration updates.
It also keeps track of information about what changes have occurred and whether
they are suspicious. Suspicious changes include adding configuration entries
that are not used anywhere, or typechanges of existing entries.

The easiest way to inspect this information is from the commandline using the
:ref:`print_config` command or alternatively the ``-p / --print_config``
:ref:`flag <cmdline_print_config>`.
The config is also passed to the observers as part of the
:ref:`started_event <event_started>` or the :ref:`queued_event <event_queued>`.
It is also available through the :ref:`api_run` through ``run.config`` and ``run.config_modifications``.
Finally the individual values can be directly accessed during a run through
:ref:`configuration_injection` or also the whole config using the ``_config``
:ref:`special value <special_values>`.


Experiment Info
===============
The experiment_info includes the name and the base directory of the experiment,
a list of source files, a list of dependencies, and, optionally, information
about its git repository.

This information is available as a dictionary from the :ref:`Run object <api_run>` through
``run.experiment_info``. And it is also passed to (and stored by) the observers
as part of the :ref:`started_event <event_started>` or the
:ref:`queued_event <event_queued>`.

Source Code
-----------
To help ensure reproducibility, Sacred automatically discovers the python
sources of an experiment and stores them alongside the run.
That way the version of the code used for running the experiment is always
available with the run.

The auto-discovery is using inspection of the imported modules and comparing them
to the local file structure.
This process should work in >95% of the use cases. But in case it fails one can
also manually add source files using :py:meth:`~sacred.Ingredient.add_source_file`.

The list of sources is accessible through ``run.experiment_info['sources']``.
It is a list of tuples of the form ``(filename, md5sum)``.
It can also be inspected using the :ref:`print_dependencies` command.

Version Control
---------------
If the experiment is part of a Git repository, Sacred will also
collect the url of the repository, the current commit hash and whether the
repository is dirty (has uncommitted changes).

This information can be inspected using the :ref:`print_dependencies` command.
But it is also available from ``run.experiment_info['repositories']``, as a
list of dictionaries of the form
``{'url': URL, 'commit': COMMIT_HASH, 'dirty': True}``.

To disable this, pass ``save_git_info=False`` to the ``Experiment``
or ``Ingredient`` constructor.


Dependencies
------------
Sacred also tries to auto-discover the package dependencies of the experiment.
This again is done using inspection of the imported modules and trying to figure
out their versions.
Like the source-code autodiscovery, this should work most of the time. But
it is also possible to manually add dependencies using
:py:meth:`~sacred.Ingredient.add_package_dependency`.

The easiest way to inspect the discovered package dependencies is via the
:ref:`print_dependencies` command.
But they are also accessible from ``run.experiment_info['dependencies']`` as
a list of strings of the form ``package==version``.


Host Info
=========
Some basic information about the machine that runs the experiment (the host) is
also collected. The default host info includes:

    ===============  ==========================================
    Key              Description
    ===============  ==========================================
    cpu              The CPU model
    hostname         The name of the machine
    os               Info about the operating system
    python_version   Version of python
    gpu              Information about NVidia GPUs (if any)
    ENV              captured ENVIRONMENT variables (if set)
    ===============  ==========================================

Host information is available from the :ref:`api_run` through ``run.host_info``.
It is sent to the observers by the :ref:`started_event <event_started>`.

The list of captured ENVIRONMENT variables (empty by default) can be extended
by appending the relevant keys to ``sacred.SETTINGS.HOST_INFO.CAPTURED_ENV``.

It is possible to extend the host information with custom functions decorated
by :py:meth:`~sacred.host_info.host_info_gatherer` like this:

.. code-block:: python

    from sacred import host_info_gatherer
    from sacred import Experiment


    @host_info_gatherer('host IP address')
    def ip():
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip


    ex = Experiment('cool experiment',
                    additional_host_info=[ip])

    @ex.main
    def my_main():
        ...

This example will create an ``host IP address`` entry in the host_info containing the
IP address of the machine.

Live Information
================
While an experiment is running, sacred collects some live information and
reports them in regular intervals (default 10sec) to the observers via the
:ref:`heartbeat_event <heartbeat>`. This includes the captured ``stdout`` and
``stderr`` and the contents of the :ref:`info_dict` which can be used to store
custom information like training curves. It also includes the current
intermediate result if set. It can be set using the ``_run`` object:

.. code-block:: python

    @ex.capture
    def some_function(_run):
        ...
        _run.result = 42
        ...

Output capturing in sacred can be done in different modes. On linux the default
is to capture on the file descriptor level, which means that it should even
capture outputs made from called c-functions or subprocesses. On Windows the
default mode is ``sys`` which only captures outputs made from within python.

Note that, the captured output behaves differently from a console in that
it doesn't by default interpret control characters like backspace
(``'\b'``) or carriage return (``'\r'``).
As an effect, some updating progressbars or the like might me more verbose
than intended. This behavior can be changed by adding a custom filter to the
captured output. To interpret control characters like a console this would do:

.. code-block:: python

    from sacred.utils import apply_backspaces_and_linefeeds

    ex.captured_out_filter = apply_backspaces_and_linefeeds

Long running and verbose experiments can overload the observer's
storage backend. For example, the MongoObserver is limited to
16 MB per run, which can result in experiments being unexpectedly
terminated. To avoid this you can turn of output capturing by
applying a custom filter like so

.. code-block:: python

    ex.captured_out_filter = lambda captured_output: "Output capturing turned off."


Metrics API
-----------
You might want to measure various values during your experiments, such as
the progress of prediction accuracy over training steps.

Sacred supports tracking of numerical series (e.g. int, float) using the Metrics API.
If the value is a `pint.Quantity https://pint.readthedocs.io/en/stable/`_, the units will also be tracked.
To access the API in experiments, the experiment must be running and the variable referencing the current experiment
or run must be available in the scope. The ``_run.log_scalar(metric_name, value, step)`` method takes
a metric name (e.g. "training.loss"), the measured value and the iteration step in which the value was taken.
If no step is specified, a counter that increments by one automatically is set up for each metric.

Step should be an integer describing the position of the value in the series. Steps can be numbered either sequentially
0, 1, 2, 3, ... or they may be given a different meaning, for instance the current iteration round.
The earlier behaviour can be achieved automatically when omitting the step parameter.
The latter approach is useful when logging occurs only every e.g. 10th iteration:
The step can be first 10, then 20, etc.
In any case, the numbers should form an increasing sequence.

.. code-block:: python

    @ex.automain
    def example_metrics(_run):
        counter = 0
        while counter < 20:
            counter+=1
            value = counter
            ms_to_wait = random.randint(5, 5000)
            time.sleep(ms_to_wait/1000)
            # This will add an entry for training.loss metric in every second iteration.
            # The resulting sequence of steps for training.loss will be 0, 2, 4, ...
            if counter % 2 == 0:
               _run.log_scalar("training.loss", value * 1.5, counter)
            # Implicit step counter (0, 1, 2, 3, ...)
            # incremented with each call for training.accuracy:
            _run.log_scalar("training.accuracy", value * 2)
            # Log an entry with units
            ureg = pint.UnitRegistry()
            _run.log_scalar("training.distance", value * 2 * ureg.meter)
            # Another option is to use the Experiment object (must be running)
            # The training.diff has its own step counter (0, 1, 2, ...) too
            ex.log_scalar("training.diff", value * 2)


Currently, the information is collected only by the following observers:

* :ref:`mongo_observer`
    * Metrics are stored in the ``metrics`` collection of MongoDB and are identified by their name (e.g. "training.loss") and the experiment run id they belong to.
* :ref:`file_observer`
    * metrics are stored in the file ``metrics.json`` in the run id's directory and are organized by metric name (e.g. "training.loss").
* :ref:`google_cloud_storage_observer`
* :ref:`s3_observer`


Metrics Records
...............

A metric record is composed of the metric name, the id of the corresponding experiment run,
and of the measured values, arranged in an array in the order they were captured using the ``log_scalar(...)``
function.
For the value located in the i-th index (``metric["values"][i]``),
the step number can be found in ``metric["steps"][i]`` and the time of the measurement in ``metric["timestamps"][i]``.

    ==================  =======================================================
    Key                 Description
    ==================  =======================================================
    ``_id``             Unique identifier
    ``name``            The name of the metric (e.g. training.loss)
    ``run_id``          The identifier of the run (``_id`` in the runs collection)
    ``steps``           Array of steps (e.g. ``[0, 1, 2, 3, 4]``)
    ``values``          Array of measured values
    ``timestamps``      Array of times of capturing the individual measurements
    ``units``           Units of the measurement (or None)
    ==================  =======================================================


Resources and Artifacts
=======================
It is possible to add files to an experiment, that will then be added to the database
(or stored by whatever observer you are using).
Apart from the source files (that are automatically added) there are two more
types of files: Resources and Artifacts.

Resources
---------
Resources are files that are needed by the experiment to run, such as datasets
or further configuration files.
If a file is opened through :py:meth:`~sacred.experiment.Experiment.open_resource`
then sacred will collect information about that file and send it to the observers.
The observers will then store the file, but not duplicate it, if it is already stored.


Artifacts
---------
Artifacts, on the other hand, are files that are produced by a run.
They might, for example, contain a detailed dump of the results or the weights
of a trained model.
They can be added to the run by :py:meth:`~sacred.experiment.Experiment.add_artifact`
Artifacts are stored with a name, which (if it isn't explicitly specified)
defaults to the filename.



Bookkeeping
===========
Finally, Sacred stores some additional bookkeeping information, and some custom
meta information about the runs.
This information is reported to the observers as soon as it is available, and
can also be accessed through the :ref:`Run object <api_run>` using the
following keys:

    ==================  =======================================================
    Key                 Description
    ==================  =======================================================
    ``start_time``      The datetime when this run was started
    ``stop_time``       The datetime when this run stopped
    ``heartbeat_time``  The last time this run communicated with the observers
    ``status``          The status of the run (see below)
    ``fail_trace``      The stacktrace of an exception that occurred (if so)
    ``result``          The return value of the main function (if successful)
    ==================  =======================================================

.. note::
    All stored times are UTC times!


Status
------
The status describes in what state a run currently is and takes one of the
following values:

    ===============  =========================================================
    Status           Description
    ===============  =========================================================
    ``QUEUED``       The run was just :ref:`queued <queuing>` and not run yet
    ``RUNNING``      Currently running (but see below)
    ``COMPLETED``    Completed successfully
    ``FAILED``       The run failed due to an exception
    ``INTERRUPTED``  The run was cancelled with a :py:class:`KeyboardInterrupt`
    ``TIMED_OUT``    The run was aborted using a :py:class:`~sacred.utils.TimeoutInterrupt`
    *[custom]*       A custom py:class:`~sacred.utils.SacredInterrupt` occurred
    ===============  =========================================================

If a run crashes in a way that doesn't allow Sacred to tell the observers
(e.g. power outage, kernel panic, ...), then the status of the crashed run
will still be ``RUNNING``.
To find these *dead* runs, one can look at the ``heartbeat_time`` of the runs
with a ``RUNNING`` status:
If the ``heartbeat_time`` lies significantly longer in the past than the
heartbeat interval (default 10sec), then the run can be considered ``DEAD``.

Meta Information
----------------
The meta-information is meant as a place to store custom information about a
run once in the beginning.
It can be added to the run by passing it to
:py:meth:`~sacred.experiment.Experiment.run`, but some commandline flags or
tools also add meta information.
It is reported to the observers as part of the
:ref:`started_event <event_started>` or the :ref:`queued_event <event_queued>`.
It can also be accessed as a dictionary through the ``meta_info`` property of
the :ref:`Run object <api_run>`.
The builtin usecases include:

    ===============  =========================================================
    Key              Description
    ===============  =========================================================
    ``command``      The name of the command that is being run
    ``options``      A dictionary with all the commandline options
    ``comment``      A comment for that run (added by the :ref:`comment flag <comment_flag>`)
    ``priority``     A priority for scheduling queued runs (added by the :ref:`priority flag <cmdline_priority>`)
    ``queue_time``   The datetime when this run was queued (stored automatically)
    ===============  =========================================================
