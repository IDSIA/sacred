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

## API description:

The goal is to make the API easier to understand. 


* We add a new class: `Config`.

* `Ingredient` is not needed anymore, and deprecated.

* There is no config scopes. They are deprecated too.

* The API of `Experiment` and `Run` does not change at all.

* Ingredients are replaced by functions which can be activated either from the command line or when creating the Experiment.

* No local variable gathering, injections or override. In short, no black magic.

* Classes and functions can be put in the config, but only the full name will be saved with the Observers.

* We have a Config object now, and all the command lines updates are done at the end of the constructor. The Experiment does not modify the Config object unless specifically asked by the user, with the `ex.run(config_updates=...)` for example.

* The idiomatic way to use this new API is to craft the `Config` object, update it from the command line, and then unpack it progressively as you call functions with the unpack operator `**`, because a `Config` will be a subclass of `dict` (I hope it doesn't come back to bite us later). Of course if your experiment is very big, you'll end up with a very big config object that will be given at the start, but that's to be expected of a computer program.

### The parameter class:

It's only pseudo-code.

```python
class Parameter:

    def __init__(self, value, description=None, delayed=False, type=None):
        self.value = value
        self.description = description
        self.delayed = delayed
        self.type = type
```


### The Config class:

It's only pseudo-code.

The `Config` class should support the dotted access `condig.dodo[2].dada` and `config['dodo'][2]['dada']`. Since there is no black magic anymore, this should be only an implementation detail, and feasible without too much work with a munchify.

A `Config` object can be used independently of an `Experiment`. A `Config` object can contain another `Config` object.


```python
class Config:
    def __init__(self, dictionary=None, potential_modificaitons=None, auto=True):
        """If auto=False, you're free to manipulate this object however you like.
        This class supports dotted access.
        """
        self.dictionary = dictionary or {}
        self.potential_modifications = potential_modificaitons or []
        self.parameters_descriptions = {}
        if auto:
            self.gather_parameters_descriptions()
            self.update_with_sys_argv()
            self.gather_parameters_descriptions()
            self.evaluate_delayed_parameters()

    def update_with_sys_argv(self):
        """
        Do the command line updates, use the potential_modifications if
        they are present in sys.argv.
        """
        ...

    def gather_parameters_descriptions(self):
        """Traverse the dictionary, sub-dictionaries and lists, fill the 
        parameters_description and replace the parameters with their values.
        """
        ...

    def evaluate_delayed_parameters(self):
        """Traverse the dictionary and evaluate the delayed parameters."""
        ...
        
    def add_potential_modifications(self, new_potential_modification):
        self.potential_modifications.append(new_potential_modification)
```


### The `get_default_args()` function

See https://github.com/IDSIA/sacred/pull/646 for the proof of concept.

```python
def get_default_args(func, docstring_style=None):
    """grab the default arguments, as well as the description from the 
    docstring.
    docstring_style must be 'google' or 'numpy'. We use the parser from sphinx.
    
    It returns a Config object.
    """
    ...
```

```python
from sacred import get_default_args

def dodo(dudu: int = 4885, dada: list = [8485, 545]):
    """Example function with types documented in the docstring.

    Args:
        dudu: First parameter.
            Second line.
        dada: The second parameter.

    Returns:
        bool: The return value. True for success, False otherwise.
    """
    pass

print(get_default_args(dodo, docstring_style='google'))
# {'dudu': Parameter(4885, 'First parameter.\nSecond line.', int),
#  'dada': Parameter([8485, 545], "The second parameter.", list)}
```

### Basic example:


```python
import sacred
from sacred import Config, get_default_args

def my_main_function(batch_size=32, dataset_size=10_000, nb_epochs=50):
    # main experiment here
    ...


configuration = Config(get_default_args(my_main_function))

ex = sacred.Experiment('my_pretty_experiment')
ex.add_config(configuration)
ex.automain(my_main_function)
```


### Example with delayed evaluation of a config variable:


This handles the case where a configuration value, if not set should be evaluated based on other values present in the config.

```python
import sacred
from sacred import Parameter, Config, get_default_args

def my_main_function(batch_size=32, dataset_size=None, nb_epochs=50):
    # main experiment here
    ...

default_args = get_default_args(my_main_function)
default_args.dataset_size = Parameter(lambda config: config['batch_size'] * 100, delayed=True)

configuration = Config(default_args)

ex = sacred.Experiment('my_pretty_experiment')
ex.add_config(configuration)
ex.automain(my_main_function)
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
from sacred import Config, get_default_args


def load_dataset(dataset_size, crop_size=(30, 30), random_flip=True):
    ...


def my_main_function(batch_size=32, dataset_size=10_000, nb_epochs=50, dataset_config=None):
    # main experiment here
    my_dataset = load_dataset(dataset_size, **dataset_config)
    ...


def config_change(config):
    config.dataset_config = dict(crop_size=(50, 50), random_flip=False)
    config.dataset_size = 700


default_config = get_default_args(my_main_function)
default_config.dataset_config = get_default_args(load_dataset)
configuration = Config(default_config, potential_modifications=[config_change])


ex = sacred.Experiment('my_pretty_experiment')
ex.add_config(configuration)
ex.automain(my_main_function)

```

```bash
python my_main.py
python my_main.py with config_change
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
from sacred import Config, get_default_args

from somewhere_else import load_dataset


def my_main_function(batch_size=32, dataset_size=10_000, nb_epochs=50, dataset_config=None):
    # main experiment here
    my_dataset = load_dataset(dataset_size, **dataset_config)
    ...


def config_change1(config):
    config.dataset_config = dict(crop_size=(30, 30), random_flip=True)
    config.dataset_size = 500
    

def config_change2(config):
    config.dataset_config = dict(crop_size=(50, 50), random_flip=False)
    config.dataset_size = 700
    
    
def config_change3(config):
    config_change1(config)
    config.dataset_size = 1_000_000


potential_modifs = [config_change1, config_change2, config_change3]
configuration = Config(get_default_args(my_main_function),
                              potential_modifications=potential_modifs)


ex = sacred.Experiment('my_pretty_experiment')
ex.add_config(configuration)
ex.automain(my_main_function)           

```


### Example with descriptions of the config values:


The `Config` object will remove the `Parameters` and keep only the value, for ease of access.
It will put the descriptions somewhere else, in another attribute of the `Config` object. 
Let's say `Config.parameters_descriptions`. 

Notice the way the batch size value is accessed when getting the default dataset size. The Parameter has been removed in the constructor.


##### Recommended way:

```python
import sacred
from sacred import Parameter, Config, get_default_args


def my_main_function(batch_size=32, dataset_size=None, nb_epochs=50):
    """This is a docstring with Napoleon Google style.
    
    Napoleon numpy style can also be used.
    
    Args:
        batch_size: The batch size value
        dataset_size: A description for the
            size of the dataset... WOW 
            it's multiple lines!!! Incredible!
        nb_epochs: The number of epochs
    """
    ...


config = get_default_args(my_main_function, docstring_style='google')
config.dataset_size = Parameter(lambda config: config.batch_size * 100, delayed=True),

ex = sacred.Experiment('my_pretty_experiment')
ex.add_config(config)
ex.automain(my_main_function)

```

##### Verbose way, not recommended:

```python
import sacred
from sacred import Parameter, Config


configuration = Config(dict(
    batch_size=Parameter(32, "The batch size value"),
    dataset_size=Parameter(lambda config: config.batch_size * 100, "The dataset size", delayed=True),
    nb_epochs=Parameter(50, "The number of epochs")
))

ex = sacred.Experiment('my_pretty_experiment')
ex.add_config(configuration)

@ex.automain
def my_main_function(batch_size, dataset_size, nb_epochs):
    # main experiment here
    ...
```


### Example with dynamic population of the potential modifications.


There is a hierarchy now. Similar to ingredients.
The named config are pulled automatically and dynamically.

```python
import sacred
from sacred import Config, get_default_args

from somewhere_else import get_mnist, get_cifar


def my_main_function(dataset_size=10_000, nb_epochs=50, function_get_dataset=None, dataset_args=None):
    # main experiment here
    
    my_dataset = function_get_dataset(**dataset_args)
    my_dataset = my_dataset[:dataset_size]
    ...


def config_mnist1(config):
    config['dataset_args'] = dict(crop_size=(30, 30), random_flip=True)


def config_mnist2(config):
    config['dataset_args'] = dict(crop_size=(40, 60), random_flip=False)


def config_dataset_mnist(config):
    config.function_get_dataset = get_mnist
    config.add_potential_modification(config_mnist1)
    config.add_potential_modification(config_mnist2)
    


def config_cifar1(config):
    config.dataset_args = dict(color=True, random_flip=True)


def config_cifar2(config):
    config.dataset_args = dict(color=False, random_flip=False)


def config_dataset_cifar(config):
    config.function_get_dataset = get_cifar
    config.add_potential_modification(config_cifar1)
    config.add_potential_modification(config_cifar2)


# Here you only specify the 2 main modifications, not the 6 of them
# the other modifications will be pulled dynamically.
potential_modifs = [config_dataset_mnist, config_dataset_cifar]
configuration = Config(get_default_args(my_main_function),
                       potential_modifications=potential_modifs)


ex = sacred.Experiment('my_pretty_experiment')
ex.add_config(configuration)
ex.automain(my_main_function)           

```

From the command line:

```bash
python my_main.py with config_dataset_cifar config_cifar2
```
