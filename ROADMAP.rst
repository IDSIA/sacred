Roadmap
=======

Version 0.7: Improved Ingredients
---------------------------------

- add a way for ingredients to modify the root config
- add a pre-run hook
- add a post-run hook
- ship an ingredient that integrates with a hyperparameter optimization tool
- ship an ingredient that allows for interactivity in the experiment
- improve the ingredient example and test it
- better documentation of ingredients


Version 0.8: Simplify Reproduction
----------------------------------

Provide a means of re-running experiment directly from the database
It should download the sources and resources and run the experiment with
the config from the DB. This would make reproducing experiments extremely
easy.



Other ideas
-----------

- use Sacred with non-python experiments by making the python part a thin
  wrapper around the external program, but add tools to make them interact
  nicely.
- a config-file in the home directory that configures some behaviours of
  Sacred globally, like log-level, observers to always add, ...
- A flat file observer that produces html reports of the run
- allow adding custom flags to the command-line interface
