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
:ref:`print_config` command or alternatively the ``-P / --print_config``
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
This process should work in >95% of the usecases. But in case it fails one can
also manually add sourcefiles using :py:meth:`~sacred.Ingredient.add_source_file`.

The list of sources is accessible through ``run.experiment_info['sources']``.
It is a list of tuples of the form ``(filename, md5sum)``.
It can also be inspected using the :ref:`print_dependencies` command.

Version Control
---------------
If the experiment is part of a version control repository, Sacred will also
try to collect the url of the repository, the current commit hash and if the
repository is dirty (has uncommitted changes).
At the moment Sacred only supports git and only if ``GitPython`` is installed.

This information can be inspected using the :ref:`print_dependencies` command.
But it is also available from ``run.experiment_info['repositories']``, as a
list of dictionaries of the form
``{'url': URL, 'commit': COMMIT_HASH, 'dirty': True}``.


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
    ===============  ==========================================

Host information is available from the :ref:api_run through ``run.host_info``.
It is sent to the observers by the :ref:`started_event <event_started>`.

It is possible to extend the host information with custom functions decorated
by :py:meth:`~sacred.host_info.host_info_getter` like this:

.. code-block:: python

    from sacred import host_info_getter

    @host_info_getter
    def ip():
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip

This example will create an ``ip`` entry in the host_info containing the
IP address of the machine.

Live Information
================
While an experiment is running, sacred collects some live information and
reports them in regular intervals (default 10sec) to the observers via the
:ref:`heartbeat_event <heartbeat>`. This includes the captured ``stdout`` and
``stderr`` and the contents of the :ref:`info_dict` which can be used to store
custom information like training curves.

Output capturing in sacred is done on the file descriptor level, which means
that it should even capture outputs made from called c-functions or
subprocesses.

Note that, the captured output behaves differently from a console in that
it doesn't by default interpret control characters like backspace
(``'\b'``) or carriage return (``'\r'``).
As an effect, some updating progressbars or the like might me more verbose
than intended. This behaviour can be changed by adding a custom filter to the
captured output. To interpret control characters like a console this would do:

.. code-block:: python

    from sacred.utils import apply_backspaces_and_linefeeds

    ex.captured_out_filter = apply_backspaces_and_linefeeds


Resources and Artifacts
=======================
adding resources
adding artifacts


Other Information
=================
* once: meta info
  * comment
  * priority
  * queue time

* start time
* status
* heartbeat time



