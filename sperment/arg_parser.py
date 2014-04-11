#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals

import argparse
import collections
import json
from sperment.observers import MongoDBReporter


def recursive_update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = recursive_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("update", nargs='*',
                        help='updates to the default options of the form '
                             'foo.bar=baz')

    parser.add_argument("-O", "--config_file",
                        help="JSON file to overwrite default configuration")

    parser.add_argument("-M", "--mongo_url", nargs='?',
                        help='activate the mongoDB obeserver and optionally '
                             'pass an url',
                        const="localhost:27017")

    parser.add_argument("-m", "--mongo_database",
                        help='name of the MongoDB database to use',
                        default='sperment')

    parser.add_argument("-P", "--print_cfg_only",
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

    if args.mongo_url:
        mongo = MongoDBReporter(db_name=args.mongo_database,
                                url=args.mongo_url)
        observers.append(mongo)

    return config_updates, observers, args
