#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals

import argparse
import collections
import json
import re
from sacred.observers import MongoDBReporter

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


def parse_arguments(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument("cmd", nargs='*',
                        help='invoke a specific command +optional arguments')

    parser.add_argument("-u", "--update", nargs='+',
                        help='updates to the default options of the form '
                             'foo.bar=baz')

    parser.add_argument("-c", "--config_file",
                        help="JSON file to overwrite default configuration")

    parser.add_argument("-m", "--mongo_db", nargs='?',
                        help='Use MongoDB. Optionally specify "db_name" or '
                             '"host:port[:db_name]"',
                        const='sacred')

    parser.add_argument("-p", "--print_cfg_only",
                        help='print the configuration and exit',
                        action='store_true')

    args = parser.parse_args(argv)
    return args


def get_config_updates(args):
    config_updates = {}

    if args.config_file:
        with open(args.config_file, 'r') as f:
            config_updates = json.load(f)

    if args.update:
        updates = re.split("[\s;]+", " ".join(args.update))
        print(updates)
        for upd in updates:
            if upd == '':
                continue
            split_update = upd.split('=')
            assert len(split_update) == 2
            path, value = split_update
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
                converted_value = json.loads(value)
            current_option[split_path[-1]] = converted_value
    return config_updates


def get_observers(args):
    observers = []
    if args.mongo_db:
        url, db_name = parse_mongo_db_arg(args.mongo_db)
        mongo = MongoDBReporter(db_name=db_name, url=url)
        observers.append(mongo)

    return observers
