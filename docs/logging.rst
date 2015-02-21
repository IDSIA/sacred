Logging
*******
Sacred used the python `logging <https://docs.python.org/2/library/logging.html>`_
module to log some basic information about the execution. It also makes it easy
for you to integrate that logging with your code.

.. _log_levels:

Adjusting Log-Levels
====================
If you run the hello_world example you will see the following output::

    >> python hello_world.py
    INFO - hello_world - Running command 'main'
    INFO - hello_world - Started
    Hello world!
    INFO - hello_world - Completed after 0:00:00

The lines starting with ``INFO`` are logging outputs. They can be suppressed by
adjusting the loglevel. This can be done via the command-line like with the
``-l`` option::

    >> python hello_world -l ERROR
    Hello world!

The specified level can be either a string or an integer:

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

Integrate Logging Into Your Experiment
======================================
If you want to make use of the logging mechanism for your own experiments the
easiest way is to use the special ``_log`` argument in your captured functions:

.. code-block:: python

    @ex.capture
    def some_function(_log):
        _log.warning('My warning message!')

This will by default print a line like this::

    WARNING - some_function - My warning message!

The ``_log`` is a standard
`Logger object <https://docs.python.org/2/library/logging.html#logger-objects>`_
for your function, as a child logger of the experiments main logger.
So it allows calls to ``debug``, ``info``, ``warning``, ``error``, ``critical``
and some more. Check out the documentation to see what you can do with them.

Customize the Logger
====================
It is easy to customize the logging behaviour of your experiment by just
providing a custom
`Logger object <https://docs.python.org/2/library/logging.html#logger-objects>`_
to your experiment:

.. code-block:: python

   import logging
   logger = logging.getLogger('my_custom_logger')
   ## configure your logger here
   ex.logger = logger

The custom logger will be used to generate all the loggers for all
captured functions. This way you can use all the features of the
`logging <https://docs.python.org/2/library/logging.html>`_ package. See the
``examples/log_example.py`` file for an example of this.


