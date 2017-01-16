Roadmap
=======

Improved Ingredients
--------------------

- add a way for ingredients to modify the root config
- ship an ingredient that allows for interactivity in the experiment
- improve the ingredient example and test it
- better documentation of ingredients


Run from Database
-----------------

Provide a means of running experiment directly from the database.
It should download the sources and resources and run the experiment with
the config from the DB.
Together with the queue-option this would allow to use Sacred for managing runs
in a distributed fashion.
Also, this would make reproducing experiments extremely easy.



Other Ideas
-----------

- add more examples for common usecases like tensorflow, theano, ...
- use Sacred with non-python experiments by making the python part a thin
  wrapper around the external program, but add tools to make them interact
  nicely.
- a config-file in the home directory that configures some behaviours of
  Sacred globally, like log-level, observers to always add, ...
- provide a unified interface to query the observers akin to the TinyDBReader
- provide tools to generate reports, overview tables and plots.
