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

* Handling seeding.

## API description:

The goal is to make the API easier to understand. We add a new class: `Configuration`.

* `Ingredient` is not needed anymore. 

* There is no config scopes.

* Ingredients are replaced by functions which can be activated either from the command line or when creating the Experiment.

* No local variable gathering, injections or override. In short, no black magic.

* Classes and functions can be put in the config, but only the full name will be saved with the Observers.

* We have a Configuration object now, and all the command lines updates are done at the end of the constructor. The Experiment does not modify the Configuration object unless specifically asked by the user, with the `ex.run(config_updates=...)` for example.

* We don't deprecate anything at the moment, we just add a new class.

### Basic example:


```python
import sacred
from sacred import Configuration


configuration = Configuration(dict(batch_size=32, dataset_size=10_000, nb_epochs=50))

ex = sacred.Experiment('my_pretty_experiment')

ex.add_config(configuration)

@ex.automain
def my_main_function(batch_size, dataset_size, nb_epochs):
    # main experiment here
    ...
```


### Example with delayed evaluation of a config variable:


This handles the case where a configuration value, if not set should be evaluated based on other values present in the config.

If the `Delayed` object is present even after all overrides from the command lines and other, it is evaluated before starting the Experiment.

```python
import sacred
from sacred import Parameter, Configuration


configuration = Configuration(dict(
    batch_size=32, 
    dataset_size=Parameter(lambda config: config['batch_size'] * 100, delayed=True),
    nb_epochs=50
))


ex = sacred.Experiment('my_pretty_experiment')
                       
ex.add_config(configuration)

@ex.automain
def my_main_function(batch_size, dataset_size, nb_epochs):
    # main experiment here
    ...
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
from sacred import Configuration


def config_change1(config):
    config['dataset_config'] = dict(crop_size=(30, 30), random_flip=True)
    config['dataset_size'] = 500
    

def config_change2(config):
    config['dataset_config'] = dict(crop_size=(50, 50), random_flip=False)
    config['dataset_size'] = 700


configuration = Configuration(dict(batch_size=32, dataset_size=10_000, nb_epochs=50),
                       potential_modifications=[config_change1, config_change2])


ex = sacred.Experiment('my_pretty_experiment')

ex.add_config(configuration)

@ex.automain
def my_main_function(batch_size, dataset_size, nb_epochs, dataset_config):
    # main experiment here
    my_dataset = load_dataset(dataset_size, **dataset_config)
    ...
```

```bash
python my_main.py with config_change1
python my_main.py with config_change2
```

By default, when calling the potential_modification from the command line, 
you should specify the `__name__` of the function. If you want to be able to say exactly which name you want, you can do:

```python
@sacred.potential_modification('pretty_name_here')
def config_change2849459(config):
    ...
```

```bash
python my_main.py with pretty_name_here
```


### Example with config updates depending on each other


`config_change3` depend on some parameters of `config_change1`.

```python
import sacred
from sacred import Configuration

from somewhere_else import load_dataset


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
configuration = Configuration(dict(batch_size=32, dataset_size=10_000, nb_epochs=50),
                       potential_modifications=potential_modifs)


ex = sacred.Experiment('my_pretty_experiment')

ex.add_config(configuration)

@ex.automain           
def my_main_function(batch_size, dataset_size, nb_epochs, dataset_config):
    # main experiment here
    my_dataset = load_dataset(dataset_size, **dataset_config)
    ...
```


### Example with descriptions of the config values:


The `Configuration` object will remove the `Parameters` and keep only the value, for ease of access.
It will put the descriptions somewhere else, in another attribute of the `Configuration` object. 
Let's say `Configuration.values_descriptions`. 

Notice the way the batch size value is accessed when getting the default dataset size. The Parameter has been removed in the constructor.

```python
import sacred
from sacred import Parameter, Configuration


configuration = Configuration(dict(
    batch_size=Parameter(32, "The batch size value"),
    dataset_size=Parameter(lambda config: config['batch_size'] * 100, "The dataset size", delayed=True),
    nb_epochs=Parameter(50, "The number of epochs")
))
print(configuration['batch_size'])  # will print 32, not a Parameter.

ex = sacred.Experiment('my_pretty_experiment')
                       
ex.add_config(configuration)

@ex.automain
def my_main_function(batch_size, dataset_size, nb_epochs):
    # main experiment here
    ...
```


### Example with dynamic population of the potential modifications.


There is a hierarchy now. Similar to ingredients.

```python
import sacred
from sacred import Configuration

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


# Here you only specify the 2 main modifications, not the 6 of them
# the other modifications will be pulled dynamically.
potential_modifs = [config_dataset_mnist, config_dataset_cifar]
configuration = Configuration(dict(dataset_size=10_000, nb_epochs=50),
                       potential_modifications=potential_modifs)


ex = sacred.Experiment('my_pretty_experiment')

ex.add_config(configuration)

@ex.automain           
def my_main_function(dataset_size, nb_epochs, function_get_dataset, dataset_args):
    # main experiment here
    
    my_dataset = function_get_dataset(**dataset_args)
    my_dataset = my_dataset[:dataset_size]
    ...
```

From the command line:

```bash
python my_main.py with config_dataset_cifar config_cifar2
```


### Example with default parameters.

We'll provide a function `sacred.get_default_args(some_function)` which will extract the default arguments and their values to make a dictionary. The you should be able to use that in the configs. 



```python
import sacred
from sacred import Configuration, get_default_args


def get_mnist(crop_size, random_flip=True, brightness=0.5):
    ...
    
print(get_default_args(get_mnist))
# {'random_flip': True, 'brightness': 0.5}

def config_mnist1(config):
    config['dataset_args'].update(dict(crop_size=(30, 30), random_flip=True))


def config_mnist2(config):
    config['dataset_args'].update(dict(crop_size=(40, 60), random_flip=False))


def config_dataset_mnist(config):
    config['function_get_dataset'] = get_mnist
    config['dataset_args'] = get_default_args(get_mnist)
    # the brightness is now in the config!
    
    config.add_potential_modification(config_mnist1)
    config.add_potential_modification(config_mnist2)
    

configuration = Configuration(dict(dataset_size=10_000, nb_epochs=50),
                       potential_modifications=[config_dataset_mnist])


ex = sacred.Experiment('my_pretty_experiment')

ex.add_config(configuration)

@ex.automain           
def my_main_function(dataset_size, nb_epochs, function_get_dataset, dataset_args):
    # main experiment here
    
    my_dataset = function_get_dataset(**dataset_args)
    my_dataset = my_dataset[:dataset_size]
    ...
```


### dotted access

The config object should support the dotted access `condig.dodo[2].dada` instead of `config['dodo'][2]['dada']`. Since there is no black magic anymore, this should be only an implementation detail, and feasible without too much work with a munchify.
