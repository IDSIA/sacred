Release History
---------------

0.5.1 (2014-??-??)
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
* Style: Lots of pep8 and pylint fixes

0.5 (2014-09-22)
++++++++++++++++
* First public release of Sacred