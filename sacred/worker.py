#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import time
import argparse
import signal
import sys
import os
import tempfile
import gridfs
import pymongo
from shutil import copy2
import json
from pkg_resources import parse_version

from sacred.observers import MongoObserver


class MongoAssistant(object):
    def __init__(self, experiment, observer, version_policy='newer'):
        self.ex = experiment
        self.observer = observer
        self.version_policy = version_policy
        self.exit = False

    def get_run(self, criterion):
        return self.observer.runs.find_one(criterion)

    def get_sources_hashs(self, run):
        for name, s_id in run['experiment']['sources']:
            s = self.observer.fs.get(s_id)
            yield name, s.md5

    def run_from_db(self, criterion):
        ex_info = self.ex.get_experiment_info()

        for trials in range(10):
            run = self.get_run(criterion)
            if run is None:
                raise IndexError('No scheduled run found')

            print('[WORKER]: Found matching run with id={}'.format(run['_id']))
            # verify the run
            _check_names(ex_info['name'], run['experiment']['name'])

            _check_sources(ex_info['sources'], self.get_sources_hashs(run))
            run['experiment']['sources'] = ex_info['sources']  # FIXME: dirty hack to avoid bug in MongoObserver
            _check_dependencies(ex_info['dependencies'],
                                run['experiment']['dependencies'],
                                self.version_policy)

            # set status to INITIALIZING to prevent others from
            # running the same Run.
            old_status = run['status']
            run['status'] = 'INITIALIZING'
            replace_summary = self.observer.runs.replace_one(
                {'_id': run['_id'], 'status': old_status},
                replacement=run)
            if replace_summary.modified_count == 1:
                break  # we've successfully acquired a run
            else:
                print('[WORKER]: Failed at claiming this run. Onto the next....')
            # otherwise we've been too slow and should try again
        else:
            raise IndexError("Something went wrong. We've not been able to "
                             "acquire a run for 10 attempts.")

        print('[WORKER]: all good: starting...')
        obs = self.get_observer_copy(overwrite=run)
        self.ex.observers.append(obs)

        # run the experiment based on the run
        # TODO: also pass options? are they stored when queued?
        res = self.ex.run(run['command'], config_updates=run['config'])

        # remove the extra observer
        self.ex.observers.remove(obs)
        return res

    def get_observer_copy(self, overwrite=None):
        runs = self.observer.runs
        fs = self.observer.fs
        priority = self.observer.priority
        return MongoObserver(runs, fs, overwrite, priority)

    def exit_gracefully(self, signal, frame):
        if self.exit:
            sys.exit(0)
        else:
            print("Interruption signal has been registered - will exit after completing experiment.")
            self.exit = True


def _check_dependencies(ex_dep, run_dep, version_policy):
    """Check that package dependencies are fulfilled according to policy."""


    def parse_ver(vstring):
        name, _, version = vstring.partition('==')
        return name, parse_version(version)
    ex_dep = dict([parse_ver(v) for v in ex_dep])

    check_version = {
        'newer': lambda ex, name, b: name in ex and ex[name] >= b,
        'equal': lambda ex, name, b: name in ex and ex[name] == b,
        'exists': lambda ex, name, b: name in ex
    }[version_policy]
    for name, ver in [parse_ver(v) for v in run_dep]:
        assert check_version(ex_dep, name, ver), \
            "{} mismatch: ex={}, run={}".format(name, ex_dep[name], ver)


def _check_sources(ex_sources, run_sources):
    """Check that sources match."""
    for ex_source, run_source in zip(ex_sources, run_sources):
        if not ex_source == tuple(run_source):
            raise KeyError('Source files did not match: experiment:'
                           ' {} [{}] != {} [{}] (run)'.format(
                            ex_source[0], ex_source[1],
                            run_source[0], run_source[1]))


def _check_names(ex_name, run_name):
    """Verify that experiment names match."""
    if not ex_name == run_name:
        raise KeyError('experiment names did not match: experiment name '
                       '{} != {} (run name)'.format(ex_name, run_name))


def write_file(base_dir, filename, content, mode='t'):
    full_name = os.path.join(base_dir, filename)
    os.makedirs(os.path.dirname(full_name), exist_ok=True)
    with open(full_name, 'w' + mode) as f:
        f.write(content)


def get_sources(run_entry, fs):
    return {s[0]: fs.get(s[1]) for s in run_entry['experiment']['sources']}


def get_resources(run_entry, fs):
    return {s[0]: fs.get(s[1]) for s in run_entry['resources']}


run_entry = runs.find_one({'status': 'COMPLETED'})
worker_dir = os.path.abspath('./SacredWorker/')
additional_files = ['constants.py', 'layernorm.py', 'noiselib.npy']
additional_requirements = ['sklearn', 'h5py']
required_packages = []

os.makedirs(worker_dir, exist_ok=True)
run_dir = tempfile.mkdtemp(dir=worker_dir,
                               prefix='run{_id}_'.format(**run_entry))


def get_truncated_python_version(run_entry):
    return '{}.{}'.format(*parse_version(run_entry['host']['python_version'])
                          ._version.release[:2])




def make_docker_dir(run_entry, run_dir, fs, add_requirements=(),
                    add_files=()):
    os.makedirs(run_dir, exist_ok=True)
    requirements = "\n".join(run_entry['experiment']['dependencies'] +
                             list(add_requirements))
    write_file(run_dir, 'requirements.txt', requirements)

    sources = get_sources(run_entry, fs)
    for filename, fp in sources.items():
        write_file(run_dir, filename, fp.read().decode())

    resources = get_resources(run_entry, fs)
    for filename, fp in resources.items():
        write_file(run_dir, filename, fp.read().decode())

    for filename in add_files:
        copy2(filename, run_dir)

    config_filename = 'config.json'
    write_file(run_dir, config_filename, json.dumps(run_entry['config']))

    mainfile = run_entry['experiment']['mainfile']
    command = run_entry['command']
    python_version = get_truncated_python_version(run_entry)

    apt_command = ''
    if required_packages:
        apt_command = '''
    RUN apt-get update && apt-get install -y \\
    {} \\
    && rm -rf /var/lib/apt/lists/*'''.format(' \\\n'.join(required_packages))

    # Dockerfile
    dockerfile = """# Use an official Python runtime as a parent image
    FROM python:{python_version}-slim
    
    # Set the working directory to /app
    WORKDIR /run
    
    {apt_command}
    
    RUN pip install -U pip pymongo
    
    # Install any needed packages specified in requirements.txt
    RUN pip install -r requirements.txt
    
    
    # Copy the current directory contents into the container at /app
    ADD . /run
    
    # Run when the container launches
    CMD ["python", "{mainfile}", "{command}", "with", "{config_filename}"]
    """.format(python_version=python_version,
               command=command,
               mainfile=mainfile,
               apt_command=apt_command,
               config_filename=config_filename)
    write_file(run_dir, 'Dockerfile', dockerfile)
    print(dockerfile)
