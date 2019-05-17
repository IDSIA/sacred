Welcome to Sacred's documentation!
==================================
    | *Every experiment is sacred*
    | *Every experiment is great*
    | *If an experiment is wasted*
    | *God gets quite irate*

Sacred is a tool to configure, organize, log and reproduce computational
experiments. It is designed to introduce only minimal overhead, while
encouraging modularity and configurability of experiments.

The ability to conveniently make experiments configurable is at the heart of
Sacred. If the parameters of an experiment are exposed in this way, it
will help you to:

    - keep track of all the parameters of your experiment
    - easily run your experiment for different settings
    - save configurations for individual runs in files or a database
    - reproduce your results

In Sacred we achieve this through the following main mechanisms:

    1. *Config Scopes* are functions with a ``@ex.config`` decorator, that turn
       all local variables into configuration entries. This helps to set up your
       configuration really easily.
    2. Those entries can then be used in *captured functions* via *dependency
       injection*. That way the system takes care of passing parameters around
       for you, which makes using your config values really easy.
    3. The *command-line interface* can be used to change the parameters, which
       makes it really easy to run your experiment with modified parameters.
    4. Observers log every information about your experiment and the
       configuration you used, and saves them for example to a Database.
       This helps to keep track of all your experiments.
    5. Automatic seeding helps controlling the randomness in your experiments,
       such that they stay reproducible.



Contents
========

.. toctree::
   :maxdepth: 1

   quickstart
   experiment
   configuration
   command_line
   collected_information
   observers
   randomness
   logging
   ingredients
   optional
   settings
   examples
   projects_using_sacred
   tensorflow
   apidoc
   internals


Index
=====

:ref:`genindex`

