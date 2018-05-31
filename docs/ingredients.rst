Ingredients
***********
Some tasks have to be performed in many different experiments. One way to avoid
code-duplication is of course to extract them to functions and import them. But
if those tasks have to be configured, the configuration values would still have
to be copied to every single experiment.

Ingredients are a way of defining a configuration with associated functions and
possibly commands that can be reused by many different experiments.
Furthermore they can influence the configuration and execution of experiments
by using certain hooks.

Simple Example
==============
So suppose in many experiments we always load a dataset from a given file and
then we might want to normalize it or not. As an Ingredient this could look like
that:

.. code-block:: python

    import numpy as np
    from sacred import Ingredient

    data_ingredient = Ingredient('dataset')

    @data_ingredient.config
    def cfg():
        filename = 'my_dataset.npy'
        normalize = True

    @data_ingredient.capture
    def load_data(filename, normalize):
        data = np.load(filename)
        if normalize:
            data -= np.mean(data)
        return data

Now all we have to do to use that in an Experiment is to import that ingredient
and add it:

.. code-block:: python

    from sacred import Experiment

    # import the Ingredient and the function we want to use:
    from dataset_ingredient import data_ingredient, load_data

    # add the Ingredient while creating the experiment
    ex = Experiment('my_experiment', ingredients=[data_ingredient])

    @ex.automain
    def run():
        data = load_data()  # just use the function

When you print the config for this experiment you will see an entry for the
dataset ingredient::

    ./my_experiment.py print_config
    INFO - my_experiment - Running command 'print_config'
    INFO - my_experiment - Started
    Configuration (modified, added, typechanged):
      seed = 586408722
      dataset:
        filename = 'my_dataset.npy'
        normalize = True
    INFO - my_experiment - Completed after 0:00:00

And we could of course set these parameters from the command-line using
``with 'dataset.filename="other.npy" 'dataset.normalize=False'``.

Overwriting the Default Configuration
=====================================
You can change the default configuration of an Ingredient in each Experiment by
adding :ref:`another ConfigScope <multiple_config_scopes>`:

.. code-block:: python

    from sacred import Experiment

    from dataset_ingredient import data_ingredient, load_data

    @data_ingredient.config
    def update_cfg():
        filename = 'special_dataset.npy'  # < updated

    ex = Experiment('my_experiment', ingredients=[data_ingredient])

    # ...


Adding Commands
===============
Adding commands to Ingredients works as you would expect:

.. code-block:: python

    @data_ingredient.command
    def stats(filename):
        print('Statistics for dataset "%s":' % filename)
        data = np.load(filename)
        print('mean = %0.2f' % np.mean(data))

You can call that command using dotted notation::

    >> ./my_experiment dataset.stats
    INFO - my_experiment - Running command 'dataset.stats'
    INFO - my_experiment - Started
    Statistics for dataset "my_dataset.npy":
    mean = 13.37
    INFO - my_experiment - Completed after 0:00:00

Nesting Ingredients
===================
It is possible to use Ingredients in other Ingredients

.. code-block:: python

    data_ingredient = Ingredient('dataset', ingredients=[my_subingredient])

In fact Experiments are also Ingredients, so you can even reuse Experiments as
Ingredients.

In the configuration of the Experiment there will be all the used Ingredients
and sub-Ingredients. So lets say you use an Ingredient called ``paths`` in the
``dataset`` Ingredient. Then in the configuration of your experiment you will
see two entries: ``dataset`` and ``paths`` (``paths`` is **not** nested in the
``dataset`` entry)

Explicit Nesting
----------------
If you want nested structure you can do it explicitly by changing the name of
the ``path`` Ingredient to ``dataset.path``. Then the path entry will be nested
in the dataset entry in the configuration.


Accessing the Ingredient Config
===============================
You can access the configuration of any used ingredient from ConfigScopes and
from captured functions via the name of the ingredient:

.. code-block:: python

    @ex.config
    def cfg(dataset):  # name of the ingredient here
        abs_filename = os.path.abspath(dataset['filename'])  # access 'filename'

    @ex.capture
    def some_function(dataset):   # name of the ingredient here
        if dataset['normalize']:  # access 'normalize'
            print("Dataset was normalized")

Ingredients with explicit nesting can be accessed by following their path. So
for the example of the Ingredient ``dataset.path`` we could access it like this:

.. code-block:: python

    @ex.capture
    def some_function(dataset):
        path = dataset['path']   # access the configuration of dataset.path

The only exception is, that if you want to access the configuration from another
Ingredient you can leave away their common prefix. So accessing ``dataset.path``
from ``dataset`` you could just directly access ``path`` in captured functions
and ConfigScopes.

Hooks
=====
Hooks are advanced mechanisms that allow the ingredient to affect the normal
execution of the experiment.

Pre- and Post-Run Hooks
-----------------------


Configuration Hooks
-------------------
Configuration hooks are executed during initialization and can be used to update the experiment's configuration before executing any command.

.. code-block:: python

    ex = Experiment()

    @ex.config_hook
    def hook(config, command_name, logger):
        config.update({'hook': True})
        return config

    @ex.automain
    def main(hook, other_config):
        do_stuff()

The config_hook function always has to take the 3 arguments `config` of the current configuration, `command_name`, which is the command that will be executed, and `logger`.
Config hooks are run after the configuration of the linked Ingredient (in the example above Experiment `ex`), but before any further ingredient-configurations are run. The dictionary returned by a config hook is used to update the config updates. Note that config hooks are not restricted to the local namespace of the ingredient.
