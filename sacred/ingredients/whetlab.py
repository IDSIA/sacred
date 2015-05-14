#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import whetlab
from sacred.experiment import Ingredient

whet = Ingredient('whet')


@whet.config
def cfg():
    name = ''
    api_key = None
    result_name = ''
    searchspace = {}
    description = ''  # optional


@whet.command
def init(name, searchspace, description, result_name, api_key):
    """Initialize a whetlab hyperparameter search for this experiment.

    Requires the whet.name, whet.api_key and whet.result_name and
    whet.searchspace config entries to be set.
    """
    print("Setting up a Whetlab experiment:")
    print("  * name:", name)
    print("  * parameters:", searchspace)
    print("  * description:", description)
    print("  * result name:", result_name)
    print("... ", end='')
    scientist = whetlab.Experiment(name,
                                   description=description,
                                   parameters=searchspace,
                                   outcome={'name': result_name},
                                   api_key=api_key)
    print("success!")


@whet.command
def mod(whet):
    scientist = whetlab.Experiment(whet['name'])
    job = scientist.suggest()
    locals().update(job)


@whet.post_run
def update_with_result(name, searchspace, _run):
    print('Sending result "{}" to whetlab... '.format(_run.result), end='')
    scientist = whetlab.Experiment(name)
    job = {k: _run.config[k] for k in searchspace}
    scientist.update(job, _run.result)
    print('done')





