# Sacred config v2

## Goals of this document:

* Present the API for the new way to work with sacred configs

* Make sure this API can handle all the use case that used to work before.

* Make sure that this API is intuitive and Pythonic.

* Make sure that someone who has never read the sacred docs can understand some codebase that uses sacred.

* Remove all black magic of configs. It is linked to the previous point.

* Give enough flexibility to allow implementation of many of the features requests about configs in github issues.

## Non-goals of this document:

* Describing or even caring about the migration process. It can be done at a later stage.

* Caring about looking like our old API about configs. Legacy API design should not prevent us from pushing a better API.

* Handling seeding. The seeding has been separated from the configuration process with the PR [Making the seeding more intuitive](https://github.com/IDSIA/sacred/pull/615)


## API description:

The goal is to make the API easier to understand.

* There is no more `Run` nor `Ingredient`, everything is done at the `Experiment` level. 

* There is no config scopes.

* Queuing Runs now means queuing Experiments. 

* An Experiment can be used only once. 

* Ingredients are replaced by functions which can be activated either from the command line or when creating the Experiment.

* No local variable gathering, injections or override. In short, no black magic.


### Basic example:


```python
import sacred


configuration = dict(batch_size=32, dataset_size=10_000, nb_epochs=50)


ex = sacred.Experiment('my_pretty_experiment',
                       config=configuration)
                       
def my_main_function(batch_size, dataset_size, nb_epochs):
    # main experiment here
    ...

with ex.start():
    my_main_function(**ex.config)
```


### Example with the log and run object:

```python
import sacred


configuration = dict(batch_size=32, dataset_size=10_000, nb_epochs=50)


ex = sacred.Experiment('my_pretty_experiment',
                       config=configuration)
                       
def my_main_function(batch_size, dataset_size, nb_epochs, run, logger):
    # main experiment here
    ...

with ex.start():
    my_main_function(**ex.config, run=ex.current_run, logger=ex.logger)
```


### Example with delayed evaluation of a config variable:


This handles the case where a configuration value, if not set should be evaluated based on other values present in the config.

If the `Delayed` object is present even after all overrides from the command lines and other, it is evaluated before starting the Experiment.

```python
import sacred
from sacred import Delayed


configuration = dict(
    batch_size=32, 
    dataset_size=Delayed(lambda config: config['batch_size'] * 100), 
    nb_epochs=50
)


ex = sacred.Experiment('my_pretty_experiment',
                       config=configuration)
                       
def my_main_function(batch_size, dataset_size, nb_epochs):
    # main experiment here
    ...

with ex.start():
    my_main_function(**ex.config)
```

For example:

```bash
python my_main.py with batch_size=60  # dataset_size is 6000 here
python my_main.py with dataset_size=5000  # dataset_size is 5000 here
```


### Example with selecting part of the configuration from the command line

This is a replacement for ingredients.


```python
import sacred


configuration = dict(batch_size=32, dataset_size=10_000, nb_epochs=50)

def config_change1(config):
    config['dataset_config'] = dict(crop_size=(30, 30), random_flip=True)
    config['dataset_size'] = 500
    

def config_change2(config):
    config['dataset_config'] = dict(crop_size=(30, 30), random_flip=True)
    config['dataset_size'] = 500


ex = sacred.Experiment('my_pretty_experiment',
                       config=configuration,
                       potential_modifications=[config_change1, config_change2])
                       
def my_main_function(batch_size, dataset_size, nb_epochs, dataset_config):
    # main experiment here
    my_dataset = load_dataset(dataset_size, **dataset_config)
    ...

with ex.start():
    my_main_function(**ex.config)
```

```bash
python my_main.py with config_change1
python my_main.py with config_change2
```
