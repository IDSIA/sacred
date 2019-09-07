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

* There is no more `Ingredient`. 

* There is no config scopes.

* Ingredients are replaced by functions which can be activated either from the command line or when creating the Experiment.

* No local variable gathering, injections or override. In short, no black magic.

* Classes and functions can be put in the config, but only the full name will be saved with the Observers.

* We have a Config object now, and all the command lines updates are done at the end of the constructor. The Experiment does not modify the Config object.

### Basic example:


```python
import sacred
from sacred import Config


configuration = Config(dict(batch_size=32, dataset_size=10_000, nb_epochs=50))

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
from sacred import Config


configuration = Config(dict(batch_size=32, dataset_size=10_000, nb_epochs=50))

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
from sacred import ConfigValue, Config


configuration = Config(dict(
    batch_size=32, 
    dataset_size=ConfigValue(lambda config: config['batch_size'] * 100, delayed=True), 
    nb_epochs=50
))


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

This is a replacement for named configs.


```python
import sacred
from sacred import Config



def config_change1(config):
    config['dataset_config'] = dict(crop_size=(30, 30), random_flip=True)
    config['dataset_size'] = 500
    

def config_change2(config):
    config['dataset_config'] = dict(crop_size=(50, 50), random_flip=False)
    config['dataset_size'] = 700


configuration = Config(dict(batch_size=32, dataset_size=10_000, nb_epochs=50),
                       potential_modifications=[config_change1, config_change2])


ex = sacred.Experiment('my_pretty_experiment',
                       config=configuration)

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


### Example with config updates depending on each other


`config_change3` depend on some parameters of `config_change1`.

```python
import sacred
from sacred import Config



def config_change1(config):
    config['dataset_config'] = dict(crop_size=(30, 30), random_flip=True)
    config['dataset_size'] = 500
    

def config_change2(config):
    config['dataset_config'] = dict(crop_size=(50, 50), random_flip=False)
    config['dataset_size'] = 700
    
    
def config_change3(config):
    config_change1(config)
    config['dataset_size'] = 1_000_000


potential_modifs = [config_change1, config_change2, config_change3]
configuration = Config(dict(batch_size=32, dataset_size=10_000, nb_epochs=50),
                       potential_modifications=potential_modifs)



ex = sacred.Experiment('my_pretty_experiment',
                       config=configuration)
                       
def my_main_function(batch_size, dataset_size, nb_epochs, dataset_config):
    # main experiment here
    my_dataset = load_dataset(dataset_size, **dataset_config)
    ...

with ex.start():
    my_main_function(**ex.config)
```


### Example with descriptions of the config values:


The `Config` object will remove the `ConfigValues` and keep only the value, for ease of access.
It will put the descriptions somewhere else, in another attribute of the `Config` object. 
Let's say `Config.values_descriptions`. 

Notice the way the batch size value is accessed when getting the default dataset size. The ConfigValue has been removed in the constructor.

```python
import sacred
from sacred import ConfigValue, Config


configuration = Config(dict(
    batch_size=ConfigValue(32, "The batch size value"),
    dataset_size=ConfigValue(lambda config: config['batch_size'] * 100, "The dataset size", delayed=True),
    nb_epochs=ConfigValue(50, "The number of epochs")
))
print(configuration['batch_size'])  # will print 32, not a ConfigValue.

ex = sacred.Experiment('my_pretty_experiment',
                       config=configuration)
                       
def my_main_function(batch_size, dataset_size, nb_epochs):
    # main experiment here
    ...

with ex.start():
    my_main_function(**ex.config)
```


### Example with dynamic population of the potential modifications.


There is a hierarchy now.

```python
import sacred
from sacred import Config

from somewhere_else import get_mnist, get_cifar


def config_mnist1(config):
    config['dataset_args'] = dict(crop_size=(30, 30), random_flip=True)


def config_mnist2(config):
    config['dataset_args'] = dict(crop_size=(40, 60), random_flip=False)


def config_dataset_mnist(config):
    config['function_get_dataset'] = get_mnist
    config.add_potential_modification(config_mnist1)
    config.add_potential_modification(config_mnist2)
    


def config_cifar1(config):
    config['dataset_args'] = dict(color=True, random_flip=True)


def config_cifar2(config):
    config['dataset_args'] = dict(color=False, random_flip=False)


def config_dataset_cifar(config):
    config['function_get_dataset'] = get_cifar
    config.add_potential_modification(config_cifar1)
    config.add_potential_modification(config_cifar2)


potential_modifs = [config_dataset_mnist, config_dataset_cifar]
configuration = Config(dict(dataset_size=10_000, nb_epochs=50),
                       potential_modifications=potential_modifs)



ex = sacred.Experiment('my_pretty_experiment',
                       config=configuration)
                       
def my_main_function(dataset_size, nb_epochs, function_get_dataset, dataset_args):
    # main experiment here
    
    my_dataset = function_get_dataset(**dataset_args)
    my_dataset = my_dataset[:dataset_size]
    ...

with ex.start():
    my_main_function(**ex.config)
```

From the command line:

```bash
python my_main.py with config_dataset_cifar config_cifar2
```
