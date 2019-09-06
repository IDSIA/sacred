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

* No 


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
                       
def my_main_function(batch_size, dataset_size, nb_epochs, experiment, logger):
    # main experiment here
    ...

with ex.start():
    my_main_function(**ex.config, experiment=ex, logger=ex.logger)
```


### Example with delayed evaluation of a config variable:


```python



```


