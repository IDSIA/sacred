Release History
---------------

0.7.5 (2019-06-20)
++++++++++++++++++
Last release to support Python 2.7.

* Feature: major improvements to error reporting (thanks @thequilo)
* Feature: added print_named_configs command
* Feature: added option to add metadata to artifacts (thanks @jarnoRFB)
* Feature: content type detection for artifacts (thanks @jarnoRFB)
* Feature: automatic seeding for pytorch (thanks @srossi93)
* Feature: add proxy support to telegram observer (thanks @brickerino)
* Feature: made MongoObserver fail dump dir configurable (thanks @jarnoRFB)
* Feature: added queue-based observer that better handles unreliable connections (thanks @jarnoRFB)
* Bugfix: some fixes to stdout capturing
* Bugfix: FileStorageObserver now creates directories only when starting a run (#329; thanks @thomasjpfan)
* Bugfix: Fixed config_hooks (#326; thanks @thomasjpfan)
* Bugfix: Fixed a crash when overwriting non-dict config entries with dicts (#325; thanks @thomasjpfan)
* Bugfix: fixed problem with running in conda environment (#341)
* Bugfix: numpy aware config change detection (#344)
* Bugfix: allow dependencies to be compiled libraries (thanks @jnphilipp)
* Bugfix: output colorization now works on 256 and 16 color terminals (thanks @bosr)
* Bugfix: fixed problem with tinydb observer logging (#327; thanks @michalgregor)
* Bugfix: ignore folders that have the same name as a named_config (thanks @boeddeker)
* Bugfix: setup no longer overwrites pre-configured root logger (thanks @thequilo)
* Bugfix: compatibility with tensorflow 2.0 (thanks @tarik, @gabrieldemarmiesse)
* Bugfix: fixed exception when no tee is available for stdout capturing (thanks @greg-farquhar)
* Bugfix: fixed concurrency issue with FileStorageObserver (thanks @dekuenstle)


0.7.4 (2018-06-12)
++++++++++++++++++
* Bugfix: fixed problem with postgres backend of SQLObserver (thanks @bensternlieb)
* Bugfix: fixed a problem with the interaction of ingredients and named configs
* Feature: added metrics logging to the FileStorageObserver (thanks @ummavi)


0.7.3 (2018-05-06)
++++++++++++++++++
* Feature: support custom experiment base directory (thanks @anibali)
* Feature: added option to pass existing MongoClient to MongoObserver (thanks @rueberger)
* Feature: allow setting the config docstring from named configs
* Feature: added py-cpuinfo as fallback for gathering CPU information (thanks @serv-inc)
* Feature: added support for _log argument in config function
* Bugfix: stacktrace filtering now correctly handles chained exceptions (thanks @kamo-naoyuki)
* Bugfix: resolved issue with stdout capturing sometimes loosing the last few lines
* Bugfix: fixed the overwrite option of MongoObserver
* Bugfix: fixed a problem with the heartbeat sometimes not ending
* Bugfix: fixed an error with running in interactive mode
* Bugfix: added a check for non-unique ingredient paths (thanks @boeddeker)
* Bugfix: fixed several problems with utf-8 decoding (thanks @LukasDrude, @wjp)
* Bugfix: fixed nesting structure of _config (thanks  @boeddeker)
* Bugfix: fixed crash when using git integration with empty repository (thanks @ramon-oliveira)
* Bugfix: fixed a crash with first run using sqlite backend
* Bugfix: fixed several problem with the tests (thanks @thomasjpfan)
* Bugfix: fixed racing condition in FileStorageObserver (thanks @boeddeker)
* Bugfix: fixed problem with overwriting named configs of ingredients (thanks @pimdh)
* Bugfix: removed deprecated call to inspect.getargspec()
* Bugfix: fixed problem with empty dictionaries disappearing from config updates and named configs (thanks @TomVeniat)
* Bugfix: fixed problem with commandline parsing when program name contained spaces
* Bugfix: loglevl option is now taken into account for config related warnings
* Bugfix: properly handle numpy types in metrics logging


0.7.2 (2017-11-02)
++++++++++++++++++
* API Change: added host_info to queued_event
* Feature: improved and configurable dependency discovery system
* Feature: improved and configurable source-file discovery system
* Feature: better error messages for missing or misspelled commands
* Feature: -m flag now supports passing an id for a run to overwrite
* Feature: allow captured functions to be called outside of a run (thanks @berleon)
* Bugfix: fixed issue with telegram imports (thanks @millawell)


0.7.1 (2017-09-14)
++++++++++++++++++
* Refactor: lazy importing of many optional dependencies
* Feature: added metrics API for adding live monitoring information to the MongoDB
* Feature: added integration with tensorflow for automatic capturing of LogWriter paths
* Feature: set seed of tensorflow if it is imported
* Feature: named_configs can now affect the config of ingredients
* Bugfix: failed runs now return with exit code 1 by default
* Bugfix: fixed a problem with UTF-8 symbols in stdout
* Bugfix: fixed a threading issue with the SQLObserver
* Bugfix: fixed a problem with consecutive ids in the SQLObserver
* Bugfix: heartbeat events now also serialize the intermediate results
* Bugfix: reapeatedly calling run from python with an option for adding an
          observer, no longer duplicates observers
* Bugfix: fixed a problem where **kwargs of captured functions might be modified
* Bugfix: fixed an encoding problem with the FileStorageObserver
* Bugfix: fixed an issue where determining the version of some packages would crash
* Bugfix: fixed handling of relative filepaths in the SQLObserver and the TinyDBObserver


0.7.0 (2017-05-07)
++++++++++++++++++
* Feature: host info now contains information about NVIDIA GPUs (if available)
* Feature: git integration: sacred now collects info about the git repository
           of the experiment (if available and if gitpython is installed)
* Feature: new ``--enforce-clean`` flag that cancels a run if the
           git repository is dirty
* Feature: added new TinyDbObserver and TinyDbReader (thanks to @MrKriss)
* Feature: added new SqlObserver
* Feature: added new FileStorageObserver
* Feature: added new SlackObserver
* Feature: added new TelegramObserver (thanks to @black-puppydog)
* Feature: added save_config command
* Feature: added queue flag to just queue a run instead of executing it
* Feature: added TimeoutInterrupt to signal that a run timed out
* Feature: experiments can now be run in Jupyter notebook, but will fail with
           an error by default, which can be deactivated using interactive=True
* Feature: allow to pass unparsed commandline string to ``ex.run_commandline``.
* Feature: improved stdout/stderr capturing: it now also collects non-python
           outputs and logging.
* Feature: observers now share the id of a run and it is available during
           runtime as ``run._id``.
* Feature: new ``--print_config`` flag to always print config first
* Feature: added sacred.SETTINGS as a place to configure some of the behaviour
* Feature: ConfigScopes now extract docstrings and line comments and display
           them when calling ``print_config``
* Feature: observers are now run in order of priority (settable)
* Feature: new ``--name=NAME`` option to set the name of experiment for this run
* Feature: the heartbeat event now stores an intermediate result (if set).
* Feature: ENVIRONMENT variables can be captured as part of host info.
* Feature: sped up the applying_lines_and_backfeeds stdout filter. (thanks to @remss)
* Feature: adding resources by name (thanks to @d4nst)
* API Change: all times are now in UTC
* API Change: significantly changed the mongoDB layout
* API Change: MongoObserver and FileStorageObserver now use consecutive
              integers as _id
* API Change: the name passed to Experiment is now optional and defaults to the
              name of the file in which it was instantiated.
              (The name is still required for interactive mode)
* API Change: Artifacts can now be named, and are stored by the observers under
              that name.
* API Change: Experiment.run_command is deprecated in favor of run, which now
              also takes a command_name parameter.
* API Change: Experiment.run now takes an options argument to add
              commandline-options also from python.
* API Change: Experiment.get_experiment_info() now returns source-names as
              relative paths and includes a separate base_dir entry
* Dependencies: Migrated from six to future, to avoid conflicts with old
                preinstalled versions of six.
* Bugfix: fixed a problem when trying  to set the loglevel to DEBUG
* Bugfix: type conversions from None to some other type are now correctly ignored
* Bugfix: fixed a problem with stdout capturing breaking tools that access
          certain attributes of ``sys.stdout`` or ``sys.stderr``.
* Bugfix: @main, @automain, @command and @capture now support functions with
           Python3 style annotations.
* Bugfix: fixed a problem with config-docs from ingredients not being propagated
* Bugfix: fixed setting seed to 0 being ignored

0.6.10 (2016-08-08)
+++++++++++++++++++
* Bugfix: fixed a problem when trying  to set the loglevel to DEBUG
* Bugfix: fixed a random crash of the heartbeat thread (see #101).
* Feature: added --force/-f option to disable errors and warnings concerning
           suspicious changes. (thanks to Yannic Kilcher)
* Feature: experiments can now be run in Jupyter notebook, but will fail with
           an error by default, which can be deactivated using interactive=True
* Feature: added support for adding a captured out filter, and a filter that
           and applies backspaces and linefeeds before saving like a terminal
           would. (thanks to Kevin McGuinness)

0.6.9 (2016-01-16)
++++++++++++++++++
* Bugfix: fixed support for ``@ex.named_config`` (was broken by 0.6.8)
* Bugfix: fixed handling of captured functions with prefix for failing on
          added unused config entries

0.6.8 (2016-01-14)
++++++++++++++++++
* Feature: Added automatic conversion of ``pandas`` datastructures in the
           custom info dict to json-format in the MongoObserver.
* Feature: Fail if a new config entry is added but it is not used anywhere
* Feature: Added a warning if no observers were added to the experiment.
           Added also an ``unobserved`` keyword to commands and a
           ``--unobserved`` commandline option to silence that warning
* Feature: Split the debug flag ``-d`` into two flags: ``-d`` now only disables
           stacktrace filtering, while ``-D`` adds post-mortem debugging.
* API change: renamed ``named_configs_to_use`` kwarg in ``ex.run_command``
              method to ``named_configs``
* API change: changed the automatic conversion of numpy arrays in the
              MongoObserver from pickle to human readable nested lists.
* Bugfix: Fixed a problem with debugging experiments.
* Bugfix: Fixed a problem with numpy datatypes in the configuration
* Bugfix: More helpful error messages when using ``return`` or ``yield`` in a
          config scope
* Bugfix: Be more helpful when using -m/--mongo_db and pymongo is not installed

0.6.7 (2015-09-11)
++++++++++++++++++
* Bugfix: fixed an error when trying to add a mongo observer via command-line

0.6.6 (2015-09-10)
++++++++++++++++++
* Feature: added -c/--comment commandline option to add a comment to a run
* Feature: added -b/--beat_interval commandline option to control the
           rate of heartbeat events
* Feature: introduced an easy way of adding custom commandline options

0.6.5 (2015-08-28)
++++++++++++++++++
* Feature: Support ``@ex.capture`` on methods (thanks to @Treora)
* Bugfix: fixed an error that occurred when a dependency module didn't have a
          the '__file__' attribute

0.6.4 (2015-06-12)
++++++++++++++++++
* Bugfix: fixed a problem where some config modification would be displayed as
          added if there where multiple ConfigScopes involved
* Bugfix: fixed a problem with tracking typechanges related to None-type
* Bugfix: fixed a crash related to MongoObserver being an unhashable type
* Bugfix: added back setslice and delslice methods to DogmaticList for
          python 2.7 compatibility

0.6.3 (2015-04-28)
++++++++++++++++++
* Bugfix: fixed a bug in the mongo observer that would always crash the final
          save
* Bugfix: automatic detection of local source files no longer wrongly detects
          non-local files in subdirectories.

0.6.2 (2015-04-16)
++++++++++++++++++
* Bugfix: fixed crash when using artifacts
* Bugfix: added resources are now saved immediately

0.6.1 (2015-04-05)
++++++++++++++++++
* Bugfix: fixed a crash when some numpy datatypes were not present
          (like numpy.float128)
* Bugfix: Made MissingDependencyMock callable so it would also correctly
          report the missing dependency when called
* Bugfix: MongoObserver would just crash the experiment if the result or the
          info are not serializable. Now it warns and tries to alter
          problematic entries such that they can be stored.

0.6 (2015-03-12)
++++++++++++++++
* Feature: With the new ``add_artifact`` function files can be added to a run
           That will fire an ``artifact event`` and they will also be stored
           in the database by the MongoObserver.
* Feature: Files can be opened through the experiment using ``open_resource``,
           which will fire a ``resource_event`` and the file is automatically
           saved to the database by the MongoObserver
* Feature: Collections used by the MongoObserver can now have a custom prefix
* Feature: MongoObserver saves all sources as separate files to the database
           using GridFS
* Feature: Sources and package dependencies can now also be manually added
* Feature: Automatically collect imported sources and dependencies also from
           ingredients
* Feature: added print_dependencies command
* Feature: With the ``--debug`` flag Sacred now automatically enters
           post-mortem debugging after an exception.
* Feature: Only filter the stacktrace if exception originated outside of Sacred
* Feature: Allow to specify a config file (json, pickle or yaml) on the
           command-line using with.
* Feature: Normal dictionaries can now be added as configuration to experiments
           using the new ``add_config`` method.
* Feature: MongoObserver now tries to reconnect to the MongoDB if connection
           is lost, and at the end of an experiment writes the entry to a
           tempfile if the reconnects failed.
* Bugfix: Invalid config keys could crash the MongoObserver or the
          print_config command. Now they are checked at the beginning and an
          exception is thrown.
* Bugfix: fixed coloring of seeds modified by or entries added by named configs
* Documentation: greatly improved the examples and added them to the docs

0.5.2 (2015-02-09)
++++++++++++++++++
* Bugfix: processor name was not queried correctly on OSX

0.5.1 (2014-10-07)
++++++++++++++++++
* Feature: added special argument ``_config`` for captured functions
* Feature: config entries that remain unchanged through config updates are no
           longer marked as modified by print_config
* Optimization: special arguments ``_rnd`` and ``_seed`` are now only generated
                if needed
* Bugfix: undocumented defective feature ``**config`` removed from
          captured functions
* Bugfix: fixed bug where indentation could lead to errors in a ``ConfigScope``
* Bugfix: added warning when attempting to overwrite an ingredient
          and it is ignored by Sacred
* Bugfix: fixed issue with synchronizing captured out at the end of the run.
          (before up to 10sec of captured output could be lost at the end)
* Bugfix: modifications on seed were not marked correctly by print_config
* Bugfix: changes to seed in NamedConfig would not correctly affect Ingredients
          Note that in order to fix this we removed the access to seed from all
          ConfigScopes. You can still set the seed but you can no longer access
          it from any ConfigScope including named ones.
          (Of course this does not affect captured functions at all.)
* Style: Lots of pep8 and pylint fixes

0.5 (2014-09-22)
++++++++++++++++
* First public release of Sacred