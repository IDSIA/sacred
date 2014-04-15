#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals

import argparse
import collections
import json
import re
from sperment.observers import MongoDBReporter

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
        return mongo_db, 'sperment'
    elif URL_DB_NAME.match(mongo_db):
        m = URL_DB_NAME.match(mongo_db)
        return m.group('url'), m.group('db_name')
    else:
        raise ValueError('mongo_db argument must have the form "db_name" or '
                         '"host:port[:db_name]" but was %s' % mongo_db)


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("update", nargs='*',
                        help='updates to the default options of the form '
                             'foo.bar=baz')

    parser.add_argument("-c", "--config_file",
                        help="JSON file to overwrite default configuration")

    parser.add_argument("-m", "--mongo_db", nargs='?',
                        help='Use MongoDB. Optionally specify "db_name" or '
                             '"host:port[:db_name]"',
                        default='sperment')

    parser.add_argument("-p", "--print_cfg_only",
                        help='print the configuration and exit',
                        action='store_true')

    args = parser.parse_args()

    config_updates = {}

    if args.config_file:
        with open(args.config_file, 'r') as f:
            config_updates = json.load(f)

    if args.update:
        for upd in args.update:
            split_update = upd.split('=')
            assert len(split_update) == 2
            path, value = split_update
            current_option = config_updates
            for p in path.split('.')[:-1]:
                if p not in current_option:
                    current_option[p] = dict()
                current_option = current_option[p]
            try:
                converted_value = json.loads(value)
            except ValueError:
                converted_value = value

            current_option[path.split('.')[-1]] = converted_value

    observers = []

    if args.mongo_db:
        url, db_name = parse_mongo_db_arg(args.mongo_db)
        mongo = MongoDBReporter(db_name=db_name, url=url)
        observers.append(mongo)

    return config_updates, observers, args
