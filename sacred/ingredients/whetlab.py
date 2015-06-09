#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

from sacred.experiment import Ingredient
from sacred.optional import whetlab

whet = Ingredient('whet')


@whet.config
def cfg():
    suggest_for = ''
    access_token = None
    searchspace = {}
    result_name = 'result'
    description = ''  # optional


@whet.config_hook
def suggest(config, command_name, logger):
    whet = config['whet']
    if whet['suggest_for']:
        try:
            scientist = whetlab.Experiment(whet['suggest_for'], resume=True)
        except ValueError:
            print("Setting up a Whetlab experiment:")
            print("  * name:", whet['suggest_for'])
            print("  * parameters:", whet['searchspace'])
            print("  * description:", whet['description'])
            print("  * result name:", whet['result_name'])
            print("... ", end='')
            scientist = whetlab.Experiment(
                whet['suggest_for'],
                description=whet['description'],
                parameters=whet['searchspace'],
                outcome={'name': whet['result_name']},
                access_token=whet['access_token'])
            print("Success")
        job = scientist.suggest()
        return job


@whet.post_run
def update_with_result(suggest_for, searchspace, _run):
    if suggest_for and _run.result is not None:
        print('Sending result "{}" to whetlab... '.format(_run.result))
        scientist = whetlab.Experiment(suggest_for, resume=True)
        job = {k: _run.config[k] for k in searchspace}
        scientist.update(job, _run.result)
        print('done')
