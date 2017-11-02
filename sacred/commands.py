#!/usr/bin/env python
# coding=utf-8
"""Defines the stock-commands that every sacred experiment ships with."""
from __future__ import division, print_function, unicode_literals

import json
import pprint
import pydoc
import os
import re
import tempfile

from collections import namedtuple
from pkg_resources import parse_version
from shutil import copy2

from sacred.config import save_config_file
from sacred.serializer import flatten
from sacred.utils import PATHCHANGE, iterate_flattened_separately

__sacred__ = True  # marks files that should be filtered from stack traces

__all__ = ('print_config', 'print_dependencies', 'save_config',
           'help_for_command')

BLUE = '\033[94m'
GREEN = '\033[92m'
RED = '\033[91m'
GREY = '\033[90m'
ENDC = '\033[0m'

LEGEND = '(' + BLUE + 'modified' + ENDC +\
    ', ' + GREEN + 'added' + ENDC +\
    ', ' + RED + 'typechanged' + ENDC +\
    ', ' + GREY + 'doc' + ENDC + ')'

ConfigEntry = namedtuple('ConfigEntry',
                         'key value added modified typechanged doc')
PathEntry = namedtuple('PathEntry', 'key added modified typechanged doc')


def _non_unicode_repr(obj, context, maxlevels, level):
    """
    Used to override the pprint format method to get rid of unicode prefixes.

    E.g.: 'John' instead of u'John'.
    """
    repr_string, isreadable, isrecursive = pprint._safe_repr(obj, context,
                                                             maxlevels, level)
    if repr_string.startswith('u"') or repr_string.startswith("u'"):
        repr_string = repr_string[1:]
    return repr_string, isreadable, isrecursive


PRINTER = pprint.PrettyPrinter()
PRINTER.format = _non_unicode_repr


def print_config(_run):
    """
    Print the updated configuration and exit.

    Text is highlighted:
      green:  value modified
      blue:   value added
      red:    value modified but type changed
    """
    final_config = _run.config
    config_mods = _run.config_modifications
    print(_format_config(final_config, config_mods))


def help_for_command(command):
    """Get the help text (signature + docstring) for a command (function)."""
    help_text = pydoc.text.document(command)
    # remove backspaces
    return re.subn('.\\x08', '', help_text)[0]


def print_dependencies(_run):
    """Print the detected source-files and dependencies."""
    print('Dependencies:')
    for dep in _run.experiment_info['dependencies']:
        pack, _, version = dep.partition('==')
        print('  {:<20} == {}'.format(pack, version))

    print('\nSources:')
    for source, digest in _run.experiment_info['sources']:
        print('  {:<43}  {}'.format(source, digest))

    if _run.experiment_info['repositories']:
        repos = _run.experiment_info['repositories']
        print('\nVersion Control:')
        for repo in repos:
            mod = RED + 'M' if repo['dirty'] else ' '
            print('{} {:<43}  {}'.format(mod, repo['url'], repo['commit']) +
                  ENDC)
    print('')


def save_config(_config, _log, config_filename='config.json'):
    """
    Store the updated configuration in a file.

    By default uses the filename "config.json", but that can be changed by
    setting the config_filename config entry.
    """
    if 'config_filename' in _config:
        del _config['config_filename']
    _log.info('Saving config to "{}"'.format(config_filename))
    save_config_file(flatten(_config), config_filename)


def docker_dir(_run, dir_name=None, command='', additional_files=(),
               additional_dependencies=(), required_packages=()):
    """
    Create a directory with all the required files to create a docker image.

    """
    if dir_name is None:
        dir_name = tempfile.mkdtemp(dir='.', prefix='run{}_'.format(
            _run.experiment_info['name']))
    dependencies = _run.experiment_info['dependencies']
    if additional_dependencies:
        dependencies += list(additional_dependencies)
    re_sources = {filename: open(filename, 'r')
                  for filename, digest in _run.experiment_info['sources']}
    _make_docker_dir(dir_name, dependencies, re_sources, _run.config,
                     _run.experiment_info['mainfile'], command,
                     _get_truncated_python_version(_run.host_info),
                     additional_files, required_packages)
    return dir_name


def run_in_virtualenv(_run, dir_name=None, command=''):
    if dir_name is None:
        dir_name = tempfile.mkdtemp(dir='.', prefix='run{}_'.format(
            _run.experiment_info['name']))
    dir_name = os.path.abspath(dir_name)

    dependencies = _run.experiment_info['dependencies']
    re_sources = {filename: open(filename, 'r')
                  for filename, digest in _run.experiment_info['sources']}
    mainfile = _run.experiment_info['mainfile']
    config = _run.config.copy()
    if 'command' in config:
        del config['command']
    if 'dir_name' in config:
        del config['dir_name']

    _make_docker_dir(dir_name, dependencies, re_sources, config, mainfile,
                     command, _get_truncated_python_version(_run.host_info),
                     [], [])
    import virtualenv
    import subprocess

    venv_dir = os.path.join(dir_name, 'venv')
    virtualenv.create_environment(venv_dir)

    req_path = os.path.join(dir_name, "requirements.txt")

    venv_script = """
        #!/bin/env bash
        cd {dir_name}
        pwd
        source venv/bin/activate
        pip install -r {req_path}
        venv/bin/python {mainfile} {command} with {config_filename}
        """.format(command=command,
                   dir_name=dir_name,
                   mainfile=mainfile,
                   config_filename='config.json',
                   req_path=req_path)
    _write_file(dir_name, 'venv_run.sh', venv_script)

    return subprocess.call(['bash', os.path.join(dir_name, 'venv_run.sh')])




def _iterate_marked(cfg, config_mods):
    for path, value in iterate_flattened_separately(cfg, ['__doc__']):
        if value is PATHCHANGE:
            yield path, PathEntry(
                key=path.rpartition('.')[2],
                added=path in config_mods.added,
                modified=path in config_mods.modified,
                typechanged=config_mods.typechanged.get(path),
                doc=config_mods.docs.get(path))
        else:
            yield path, ConfigEntry(
                key=path.rpartition('.')[2],
                value=value,
                added=path in config_mods.added,
                modified=path in config_mods.modified,
                typechanged=config_mods.typechanged.get(path),
                doc=config_mods.docs.get(path))


def _format_entry(indent, entry):
    color = ""
    indent = ' ' * indent
    if entry.typechanged:
        color = RED
    elif entry.added:
        color = GREEN
    elif entry.modified:
        color = BLUE
    if entry.key == '__doc__':
        color = GREY
        doc_string = entry.value.replace('\n', '\n' + indent)
        assign = '{}"""{}"""'.format(indent, doc_string)
    elif isinstance(entry, ConfigEntry):
        assign = indent + entry.key + " = " + PRINTER.pformat(entry.value)
    else:  # isinstance(entry, PathEntry):
        assign = indent + entry.key + ":"
    if entry.doc:
        doc_string = GREY + '# ' + entry.doc + ENDC
        if len(assign) <= 35:
            assign = "{:<35}  {}".format(assign, doc_string)
        else:
            assign += '    ' + doc_string
    end = ENDC if color else ""
    return color + assign + end


def _format_config(cfg, config_mods):
    lines = ['Configuration ' + LEGEND + ':']
    for path, entry in _iterate_marked(cfg, config_mods):
        indent = 2 + 2 * path.count('.')
        lines.append(_format_entry(indent, entry))
    return "\n".join(lines)


def _write_file(base_dir, filename, content, mode='t'):
    full_name = os.path.join(base_dir, filename)
    os.makedirs(os.path.dirname(full_name), exist_ok=True)
    with open(full_name, 'w' + mode) as f:
        f.write(content)


def _get_truncated_python_version(host_info):
    version = parse_version(host_info['python_version'])
    return '{}.{}'.format(*version._version.release[:2])


def _make_docker_dir(run_dir, requirements, re_sources, config, mainfile,
                     command, python_version, copy_files=(),
                     required_packages=()):
    os.makedirs(run_dir, exist_ok=True)

    if isinstance(requirements, (tuple, list)):
        requirements = "\n".join(requirements)
    _write_file(run_dir, 'requirements.txt', requirements)

    for filename, fp in re_sources.items():
        _write_file(run_dir, filename, fp.read())

    for filename in copy_files:
        copy2(filename, run_dir)

    _write_file(run_dir, 'config.json', json.dumps(config))

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
    
    # Copy the current directory contents into the container at /app
    ADD . /run

    {apt_command}

    RUN pip install -U pip pymongo

    # Install any needed packages specified in requirements.txt
    RUN pip install -r requirements.txt


    # Run when the container launches
    CMD ["python", "{mainfile}", "{command}", "with", "{config_filename}"]
    """.format(python_version=python_version,
               command=command,
               mainfile=mainfile,
               apt_command=apt_command,
               config_filename='config.json')
    _write_file(run_dir, 'Dockerfile', dockerfile)


def extract_info_from_run_entry(run_entry, fs):
    return {'mainfile': run_entry['experiment']['mainfile'],
            'command': run_entry['command'],
            'config': run_entry['config'],
            'python_version': _get_truncated_python_version(run_entry['host']),
            'requirements': run_entry['experiment']['dependencies'],
            'sources': {source[0]: fs.get(source[1])
                        for source in run_entry['experiment']['sources']},
            'resources': {resource[0]: fs.get(resource[1])
                          for resource in run_entry['resources']}}
