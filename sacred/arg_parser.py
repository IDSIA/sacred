#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import collections
import json
import re
from jinja2 import Template
from docopt import docopt
from sacred.observers import MongoDBReporter


USAGE_TEMPLATE = Template("""
{{ description }}

Usage:
  {{ program_name }} [run] [(with UPDATE...)] [-m DB]
  {{ program_name }} help [COMMAND]
  {{ program_name }} COMMAND [(with UPDATE...)]
  {{ program_name }} (-h | --help)


Options:
  -h --help             Print this help message and exit
  -m DB --mongo_db=DB   Add a MongoDB Observer to the experiment

Arguments:
  DB        Database specification. Can be [host:port:]db_name
  UPDATE    Configuration assignments of the form foo.bar=17
  COMMAND   Custom command to run

{% if commands | length > 0 %}Commands:{% endif %}

{% for key, value in commands.iteritems() %}
  {{ key.ljust(cmd_len) }}  {{value}}
{% endfor %}
""", trim_blocks=True)


DB_NAME_PATTERN = r"[_A-Za-z][0-9A-Za-z!#%&'()+\-;=@\[\]^_{}]{0,63}"
HOSTNAME_PATTERN = \
    r"(?=.{1,255}$)"\
         r"[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?"\
    r"(?:\.[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?)*"\
    r"\.?"
URL_PATTERN = "(?:" + HOSTNAME_PATTERN + ")" + ":" + "(?:[0-9]{1,5})"

DB_NAME = re.compile("^" + DB_NAME_PATTERN + "$")
URL = re.compile("^" + URL_PATTERN + "$")
URL_DB_NAME = re.compile("^(?P<url>" + URL_PATTERN + ")" + ":" +
                         "(?P<db_name>" + DB_NAME_PATTERN + ")$")


def recursive_update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = recursive_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def parse_mongo_db_arg(mongo_db):
    if DB_NAME.match(mongo_db):
        return 'localhost:27017', mongo_db
    elif URL.match(mongo_db):
        return mongo_db, 'sacred'
    elif URL_DB_NAME.match(mongo_db):
        m = URL_DB_NAME.match(mongo_db)
        return m.group('url'), m.group('db_name')
    else:
        raise ValueError('mongo_db argument must have the form "db_name" or '
                         '"host:port[:db_name]" but was %s' % mongo_db)

import textwrap


def parse_args(argv, description="", commands=None):
    if commands is None:
        commands = {}
    cmd_len = max([len(c) for c in commands] + [8])
    command_doc = {k: textwrap.dedent(v.__doc__ or "").strip().split('\n')[0]
                   for k, v in commands.items()}

    usage = USAGE_TEMPLATE.render(
        program_name=argv[0],
        description=description,
        commands=command_doc,
        cmd_len=cmd_len)

    return docopt(usage, [str(a) for a in argv[1:]])


def get_config_updates(updates):
    config_updates = {}
    if not updates:
        return config_updates
    for upd in updates:
        if upd == '':
            continue
        path, sep, value = upd.partition('=')
        assert sep == '=', "Missing '=' in update '%s'" % upd
        current_option = config_updates
        split_path = path.split('.')
        for p in split_path[:-1]:
            if p not in current_option:
                current_option[p] = dict()
            current_option = current_option[p]

        if value == 'True':
            converted_value = True
        elif value == 'False':
            converted_value = False
        elif value == 'None':
            converted_value = None
        elif value[0] == "'" and value[-1] == "'":
            converted_value = value[1:-1]
        else:
            try:
                converted_value = json.loads(value)
            except ValueError:
                converted_value = value
        current_option[split_path[-1]] = converted_value
    return config_updates


def get_observers(args):
    observers = []
    if args['--mongo_db']:
        url, db_name = parse_mongo_db_arg(args['--mongo_db'])
        mongo = MongoDBReporter(db_name=db_name, url=url)
        observers.append(mongo)

    return observers
