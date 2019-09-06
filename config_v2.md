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


### Basic example:


```python
import sacred


configuration = 


ex = sacred.Experiment('my_pretty_experiment')




```