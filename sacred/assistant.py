#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import pymongo
import gridfs
from datetime import datetime, timedelta
import time
from sacred.observers import MongoObserver


class MongoAssistant(object):
    def __init__(self, database, experiment, prefix='default'):
        self.db = database
        self.ex = experiment
        self.prefix = prefix
        self.runs = self.db[self.prefix].runs
        self.version_policy = 'newer'

    def get_runs_by_status(self, status):
        self.runs.find({'status': status})

    def mark_dead_runs(self):
        """
        Find all runs with a RUNNING status but no heartbeat within the last
        minute and set their status to DIED.
        """
        a_minute_ago = datetime.now() - timedelta(minutes=1)
        self.runs.update_many(
            {'status': 'RUNNING', 'heartbeat': {'$lt': a_minute_ago}},
            {'$set': {'status': 'DIED'}}
        )

    def get_status(self):
        """Return a summary of how many runs are in each status"""
        self.mark_dead_runs()
        pipeline = [{'$group': {'_id': '$status', 'count': {'$sum': 1}}}]
        return {r['_id']: r['count'] for r in self.runs.aggregate(pipeline)}

    def get_run(self, criterion):
        return self.runs.find_one(criterion)

    def run_from_db(self, criterion, version_policy='newer'):
        ex_info = self.ex.get_experiment_info()

        for trials in range(10):
            run = self.get_run(criterion)
            if run is None:
                raise IndexError('No scheduled run found')

            # verify the run
            _check_names(ex_info['name'], run['experiment']['name'])
            _check_sources(ex_info['sources'], run['experiment']['sources'])
            _check_dependencies(ex_info['dependencies'],
                                run['experiment']['dependencies'],
                                version_policy)

            # set status to INITIALIZING to prevent others from
            # running the same Run.
            old_status = run['status']
            run['status'] = 'INITIALIZING'
            replace_summary = self.runs.replace_one(
                {'_id': run['_id'], 'status': old_status},
                replacement=run)
            if replace_summary.modified_count == 1:
                break  # we've successfully acquired a run
            # otherwise we've been too slow and should try again
        else:
            raise IndexError("Something went wrong. We've not been able to "
                             "acquire a run for 10 attempts.")

        # add a matching MongoObserver to the experiment and tell it to
        # overwrite the run
        fs = gridfs.GridFS(self.db, collection=self.prefix)
        self.ex.observers.append(MongoObserver(self.runs, fs,
                                               overwrite=run))

        # run the experiment based on the run
        res = self.ex.run_command(run['command'], config_updates=run['config'])

        # remove the extra observer
        self.ex.observers.pop()
        return res


def _check_dependencies(ex_dep, run_dep, version_policy):
    from pkg_resources import parse_version
    ex_dep = {name: parse_version(ver) for name, ver in ex_dep}
    check_version = {
        'newer': lambda ex, name, b: name in ex and ex[name] >= b,
        'equal': lambda ex, name, b: name in ex and ex[name] == b,
        'exists': lambda ex, name, b: name in ex
    }[version_policy]
    for name, ver in run_dep:
        assert check_version(ex_dep, name, parse_version(ver)), \
            "{} mismatch: ex={}, run={}".format(name, ex_dep[name], ver)


def _check_sources(ex_sources, run_sources):
    for ex_source, run_source in zip(ex_sources, run_sources):
        if not ex_source == tuple(run_source):
            raise KeyError('Source files did not match: experiment:'
                           ' {} [{}] != {} [{}] (run)'.format(
                            ex_source[0], ex_source[1],
                            run_source[0], run_source[1]))


def _check_names(ex_name, run_name):
    if not ex_name == run_name:
        raise KeyError('experiment names did not match: experiment name '
                       '{} != {} (run name)'.format(ex_name, run_name))
