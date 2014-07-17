Command-Line Interface
**********************

Sacred provides you with a powerful command line interface.

Flags
=====

Logging Level
-------------
  -l LEVEL    control logging level

MongoDB Observer
----------------
  -m DB       add a MongoDB observer


``with`` config=update
======================

Works like this::

    >>> ./example run with a=10
    >>> ./example run with a=10 b=20


Print Config
============

pass

Custom Commands
===============

  - ``@ex.command`` adds custom commands to your commandline
  - the docstring is kept for help
  - it counts as a captured function so you can use all configuration
  - you can even add "unfilled config parameters" and make them required




