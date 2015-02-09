Release History
---------------

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
          and it is ignored by sacred
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