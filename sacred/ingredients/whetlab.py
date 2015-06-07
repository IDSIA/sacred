#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from sacred.experiment import Ingredient
from sacred.optional import whetlab

whet = Ingredient('whet')


@whet.config
def cfg():
    name = ''
    access_token = None
    result_name = 'result'
    searchspace = {}
    description = ''  # optional
    suggest = False


@whet.command
def init(name, searchspace, description, result_name, access_token):
    """Initialize a whetlab hyperparameter search for this experiment.

    Requires the whet.name, whet.access_token and whet.result_name and
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
                                   access_token=access_token)
    print("success!")


@whet.config_hook
def mod(whet):
    if whet['suggest'] and whet['name']:
        scientist = whetlab.Experiment(whet['name'])
        job = scientist.suggest()
        locals().update(job)
        del job


@whet.post_run
def update_with_result(name, searchspace, _run):
    if name and _run.result is not None:
        print('Sending result "{}" to whetlab... '.format(_run.result))
        scientist = whetlab.Experiment(name)
        job = {k: _run.config[k] for k in searchspace}
        scientist.update(job, _run.result)
        print('done')
