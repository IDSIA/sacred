Command-Line Interface
**********************

Sacred provides a powerful command line interface for every experiment out of
box. All you have to do to use it is to either have a method decorated with
``@ex.automain`` or to put this block at the end of your file:

.. code-block:: python

    if __name__ == '__main__':
        ex.run_commandline()


Configuration Updates
=====================
You can easily change any configuration entry using the powerful
``with`` command on the commandline. Just put ``with config=update`` after your
experiment call like this::

    >>> ./example.py with a=10
    >>> ./example.py with a=2.3 b="'FooBar'"


- You can use python syntax for the values. But watch out for the bash, it
  removes the first set of quotes.

  - if you want a string you need double quotes ``with a=1`` and
    ``with a="1"`` are both integers but ``with a="'1'"`` is a string.
  -

- You can use dotted notation for sub-entries of dictionaries



Print Config
============

pass


Flags
=====

**Help**

+------------+-----------------------------+
| ``-h``     |  Print Usage                |
+------------+                             |
| ``--help`` |                             |
+------------+-----------------------------+

This prints a help/usage message for your experiment.
It is equivalent to typing just ``help``.

**Logging Level**

+---------------------+-----------------------------+
| ``-l LEVEL``        |  control the logging level  |
+---------------------+                             |
| ``--logging=LEVEL`` |                             |
+---------------------+-----------------------------+

With this flag you can adjust the logging level.

+----------+---------------+
| Level    | Numeric value |
+==========+===============+
| CRITICAL | 50            |
+----------+---------------+
| ERROR    | 40            |
+----------+---------------+
| WARNING  | 30            |
+----------+---------------+
| INFO     | 20            |
+----------+---------------+
| DEBUG    | 10            |
+----------+---------------+
| NOTSET   | 0             |
+----------+---------------+

See :ref:`log_levels` for more details.

**MongoDB Observer**

+-------------------+--------------------------+
| ``-m DB``         |  add a MongoDB observer  |
+-------------------+                          |
| ``--mongo_db=DB`` |                          |
+-------------------+--------------------------+


This flag can be used to add a MongoDB observer to your experiment. ``DB`` must
be of the form ``db_name`` or ``[host:port:]db_name``.

See :ref:`mongo_observer` for more details.

**Debug Mode**

+-------------------+-------------------------------+
| ``-d``            |  don't filter the stacktrace  |
+-------------------+                               |
| ``--debug``       |                               |
+-------------------+-------------------------------+

This flag deactivates the stacktrace filtering. You should usually not need
this. It is mainly used for debugging Sacred.


Custom Commands
===============

  - ``@ex.command`` adds custom commands to your commandline
  - the docstring is kept for help
  - it counts as a captured function so you can use all configuration
  - you can even add "unfilled config parameters" and make them required




