Examples
********
You can find these examples in the examples directory (surprise!) of the
Sacred sources or in the
`Github Repository <https://github.com/IDSIA/sacred/tree/master/examples>`_.
Look at them for the sourcecode, it is an important part of the examples.
It can also be very helpful to run them yourself and play with the command-line
interface.

The following is just their documentation from their docstring which you can
also get by running them with the ``-h``, ``--help`` or ``help`` flags.

Hello World
===========
`examples/01_hello_world.py <https://github.com/IDSIA/sacred/tree/master/examples/01_hello_world.py>`_

.. automodule:: examples.01_hello_world

Hello Config Dict
=================
`examples/02_hello_config_dict.py <https://github.com/IDSIA/sacred/tree/master/examples/02_hello_config_dict.py>`_

.. automodule:: examples.02_hello_config_dict

Hello Config Scope
==================
`examples/03_hello_config_scope.py <https://github.com/IDSIA/sacred/tree/master/examples/03_hello_config_scope.py>`_

.. automodule:: examples.03_hello_config_scope

Captured Functions
==================
`examples/04_captured_functions.py <https://github.com/IDSIA/sacred/tree/master/examples/04_captured_functions.py>`_

.. automodule:: examples.04_captured_functions

My Commands
===========
`examples/05_my_commands.py <https://github.com/IDSIA/sacred/tree/master/examples/05_my_commands.py>`_

.. automodule:: examples.05_my_commands

Randomness
==========
`examples/06_randomness.py <https://github.com/IDSIA/sacred/tree/master/examples/06_randomness.py>`_

.. automodule:: examples.06_randomness


Less magic
==========
If you are new to Sacred, you might be surprised by the amount of new idioms it
introduces compared to standard Python. But don't worry, you don't have to use any of the
magic if you don't want to and still benefit from the excellent tracking capabilities.

`examples/07_magic.py <https://github.com/IDSIA/sacred/tree/master/examples/07_magic.py>`_
shows a standard machine learning task, that uses a lot of possible Sacred idioms:

* configuration definition through local variables
* parameter injection through captured functions
* command line interface integration through the ``ex.automain`` decorator

`examples/08_less_magic.py <https://github.com/IDSIA/sacred/tree/master/examples/08_less_magic.py>`_
shows the same task without any of those idioms. The recipe for replacing Sacred magic with
standard Python is simple.

* define your configuration in an external ``JSON`` or ``YAML`` file
* avoid the ``ex.capture`` decorator. Instead only pass ``_config`` to the main function
  and access all parameters explicitly through the configuration dictionary
* just use ``ex.main`` instead of ``ex.automain`` and call ``ex.run()``
  explicitly. This avoids the parsing of command line parameters you did not define yourself.

While we believe that using sacred idioms makes things easier by hard-wiring parameters
and giving you a flexible command line interface, we do not enforce its usage
if you feel more comfortable with classical Python. At its core Sacred is about
tracking computatonal experiments, not about any particular coding style.