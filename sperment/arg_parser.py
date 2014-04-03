#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals

import argparse
import collections
import json


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
    parser.add_argument("-O", "--option_file",
                        help="JSON file to overwrite default options")

    parser.add_argument("-U", "--update", nargs='+',
                        help='updates to the default options of the form '
                             'foo.bar=baz')

    parser.add_argument("-M", "--mongo_url", nargs='?',
                        help='the url for the mongoDB observer',
                        const="localhost:27017")

    parser.add_argument("-m", "--mongo_database",
                        help='name of the MongoDB database to use',
                        default='sperment')

    args = parser.parse_args()

    if args.option_file:
        with open(args.option_file, 'r') as f:
            option_updates = json.load(f)
    else:
        option_updates = {
        }

    if args.update:
        for upd in args.update:
            split_update = upd.split('=')
            assert len(split_update) == 2
            path, value = split_update
            current_option = option_updates
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
        from mlite.observers.mongodb import MongoDBReporter
        mongo = MongoDBReporter(db_name=args.mongo_collection,
                                url=args.mongo_url)
        observers.append(mongo)

    return option_updates, observers
