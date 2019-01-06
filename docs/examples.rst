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

Docker Setup
============
`examples/docker <https://github.com/IDSIA/sacred/tree/master/examples/docker>`_

To use Sacred to its full potential you probably want to use it together with
MongoDB and dashboards like `Omniboard <https://github.com/vivekratnavel/omniboard>`_ that have been developed for it.
To ease getting started with these services you find an exemplary ``docker-compose`` configuration in
`examples/docker <https://github.com/IDSIA/sacred/tree/master/examples/docker>`_. After installing
`Docker Engine <https://docs.docker.com/install/>`_ and `Docker Compose <https://docs.docker.com/compose/install/>`_
(only necessary for Linux) go to the directory and run::

    docker-compose up


This will pull the necessary containers from the internet and build them. This may take several
minutes.
Afterwards mongoDB should be up and running. ``mongo-express``, an admin interface for MonogDB, should now
be available on port ``8081``, accessible by the user and password set in the ``.env`` file (``ME_CONFIG_BASICAUTH_USERNAME``
and ``ME_CONFIG_BASICAUTH_PASSWORD``). ``Sacredboard ``should be available on port ``5000``. ``Omniboard`` should be
available on port ``9000``. All services will by default only be exposed to ``localhost``. If you want
to expose them on all interfaces, e.g. for the use on a server, you need to change the port mappings
in ``docker-compose.yml`` from ``127.0.0.1:XXXX:XXXX`` to ``XXXX:XXXX``. However, in this case you should
change the authentification information in ``.env`` to something more secure.