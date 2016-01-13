Release History
---------------

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