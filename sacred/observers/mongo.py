#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import pickle
import re
import os.path
import sys
import time

import bson
import gridfs
import pymongo
import sacred.optional as opt
from pymongo.errors import AutoReconnect, InvalidDocument, DuplicateKeyError
from sacred.commandline_options import CommandLineOption
from sacred.dependencies import get_digest
from sacred.observers.base import RunObserver
from sacred.serializer import flatten
from sacred.utils import ObserverError


DEFAULT_MONGO_PRIORITY = 30


def force_valid_bson_key(key):
    key = str(key)
    if key.startswith('$'):
        key = '@' + key[1:]
    key = key.replace('.', ',')
    return key


def force_bson_encodeable(obj):
    if isinstance(obj, dict):
        try:
            bson.BSON.encode(obj, check_keys=True)
            return obj
        except bson.InvalidDocument:
            return {force_valid_bson_key(k): force_bson_encodeable(v)
                    for k, v in obj.items()}

    elif opt.has_numpy and isinstance(obj, opt.np.ndarray):
        return obj
    else:
        try:
            bson.BSON.encode({'dict_just_for_testing': obj})
            return obj
        except bson.InvalidDocument:
            return str(obj)


class MongoObserver(RunObserver):
    COLLECTION_NAME_BLACKLIST = {'fs.files', 'fs.chunks', '_properties',
                                 'system.indexes', 'search_space'}
    VERSION = 'MongoObserver-0.7.0'

    @staticmethod
    def create(url='localhost', db_name='sacred', collection='runs',
               overwrite=None, priority=DEFAULT_MONGO_PRIORITY, **kwargs):
        client = pymongo.MongoClient(url, **kwargs)
        database = client[db_name]
        if collection in MongoObserver.COLLECTION_NAME_BLACKLIST:
            raise KeyError('Collection name "{}" is reserved. '
                           'Please use a different one.'.format(collection))
        runs_collection = database[collection]
        fs = gridfs.GridFS(database)
        return MongoObserver(runs_collection, fs, overwrite=overwrite,
                             priority=priority)

    def __init__(self, runs_collection, fs, overwrite=None,
                 priority=DEFAULT_MONGO_PRIORITY):
        self.runs = runs_collection
        self.fs = fs
        self.overwrite = overwrite
        self.run_entry = None
        self.priority = priority

    def queued_event(self, ex_info, command, queue_time, config, meta_info,
                     _id):
        if self.overwrite is not None:
            raise RuntimeError("Can't overwrite with QUEUED run.")
        self.run_entry = {
            'experiment': dict(ex_info),
            'command': command,
            'config': flatten(config),
            'meta': meta_info,
            'status': 'QUEUED'
        }
        # set ID if given
        if _id is not None:
            self.run_entry['_id'] = _id
        # save sources
        self.run_entry['experiment']['sources'] = self.save_sources(ex_info)
        self.insert()
        return self.run_entry['_id']

    def started_event(self, ex_info, command, host_info, start_time, config,
                      meta_info, _id):
        if self.overwrite is None:
            self.run_entry = {'_id': _id}
        else:
            if self.run_entry is not None:
                raise RuntimeError("Cannot overwrite more than once!")
            # sanity checks
            if self.overwrite['experiment']['sources'] != ex_info['sources']:
                raise RuntimeError("Sources don't match")
            self.run_entry = self.overwrite

        self.run_entry.update({
            'experiment': dict(ex_info),
            'format': self.VERSION,
            'command': command,
            'host': dict(host_info),
            'start_time': start_time,
            'config': flatten(config),
            'meta': meta_info,
            'status': 'RUNNING',
            'resources': [],
            'artifacts': [],
            'captured_out': '',
            'info': {},
            'heartbeat': None
        })

        # save sources
        self.run_entry['experiment']['sources'] = self.save_sources(ex_info)
        self.insert()
        return self.run_entry['_id']

    def heartbeat_event(self, info, captured_out, beat_time):
        self.run_entry['info'] = flatten(info)
        self.run_entry['captured_out'] = captured_out
        self.run_entry['heartbeat'] = beat_time
        self.save()

    def completed_event(self, stop_time, result):
        self.run_entry['stop_time'] = stop_time
        self.run_entry['result'] = flatten(result)
        self.run_entry['status'] = 'COMPLETED'
        self.final_save(attempts=10)

    def interrupted_event(self, interrupt_time, status):
        self.run_entry['stop_time'] = interrupt_time
        self.run_entry['status'] = status
        self.final_save(attempts=3)

    def failed_event(self, fail_time, fail_trace):
        self.run_entry['stop_time'] = fail_time
        self.run_entry['status'] = 'FAILED'
        self.run_entry['fail_trace'] = fail_trace
        self.final_save(attempts=1)

    def resource_event(self, filename):
        if self.fs.exists(filename=filename):
            md5hash = get_digest(filename)
            if self.fs.exists(filename=filename, md5=md5hash):
                resource = (filename, md5hash)
                if resource not in self.run_entry['resources']:
                    self.run_entry['resources'].append(resource)
                    self.save()
                return
        with open(filename, 'rb') as f:
            file_id = self.fs.put(f, filename=filename)
        md5hash = self.fs.get(file_id).md5
        self.run_entry['resources'].append((filename, md5hash))
        self.save()

    def artifact_event(self, name, filename):
        with open(filename, 'rb') as f:
            run_id = self.run_entry['_id']
            db_filename = 'artifact://{}/{}/{}'.format(self.runs.name, run_id,
                                                       name)
            file_id = self.fs.put(f, filename=db_filename)
        self.run_entry['artifacts'].append({'name': name,
                                            'file_id': file_id})
        self.save()

    def insert(self):
        if self.overwrite:
            return self.save()

        autoinc_key = self.run_entry['_id'] is None
        while True:
            if autoinc_key:
                c = self.runs.find({}, {'_id': 1})
                c = c.sort('_id', pymongo.DESCENDING).limit(1)
                self.run_entry['_id'] = c.next()['_id'] + 1 if c.count() else 1
            try:
                self.runs.insert_one(self.run_entry)
            except InvalidDocument:
                raise ObserverError('Run contained an unserializable entry.'
                                    '(most likely in the info)')
            except DuplicateKeyError:
                if not autoinc_key:
                    raise
            return

    def save(self):
        try:
            self.runs.replace_one({'_id': self.run_entry['_id']},
                                  self.run_entry)
        except AutoReconnect:
            pass  # just wait for the next save
        except InvalidDocument:
            raise ObserverError('Run contained an unserializable entry.'
                                '(most likely in the info)')

    def final_save(self, attempts):
        for i in range(attempts):
            try:
                self.runs.save(self.run_entry)
                return
            except AutoReconnect:
                if i < attempts - 1:
                    time.sleep(1)
            except InvalidDocument:
                self.run_entry = force_bson_encodeable(self.run_entry)
                print("Warning: Some of the entries of the run were not "
                      "BSON-serializable!\n They have been altered such that "
                      "they can be stored, but you should fix your experiment!"
                      "Most likely it is either the 'info' or the 'result'.",
                      file=sys.stderr)

        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(suffix='.pickle', delete=False,
                                prefix='sacred_mongo_fail_') as f:
            pickle.dump(self.run_entry, f)
            print("Warning: saving to MongoDB failed! "
                  "Stored experiment entry in '{}'".format(f.name),
                  file=sys.stderr)

    def save_sources(self, ex_info):
        base_dir = ex_info['base_dir']
        source_info = []
        for source_name, md5 in ex_info['sources']:
            abs_path = os.path.join(base_dir, source_name)
            file = self.fs.find_one({'filename': abs_path, 'md5': md5})
            if file:
                _id = file._id
            else:
                with open(abs_path, 'rb') as f:
                    _id = self.fs.put(f, filename=abs_path)
            source_info.append([source_name, _id])
        return source_info

    def __eq__(self, other):
        if isinstance(other, MongoObserver):
            return self.runs == other.runs
        return False

    def __ne__(self, other):
        return not self.__eq__(other)


class MongoDbOption(CommandLineOption):
    """Add a MongoDB Observer to the experiment."""

    arg = 'DB'
    arg_description = "Database specification. Can be " \
                      "[host:port:]db_name[.collection][!priority]"

    DB_NAME_PATTERN = r"[_A-Za-z][0-9A-Za-z#%&'()+\-;=@\[\]^_{}.]{0,63}"
    HOSTNAME_PATTERN = \
        r"(?=.{1,255}$)"\
        r"[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?"\
        r"(?:\.[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?)*"\
        r"\.?"
    URL_PATTERN = "(?:" + HOSTNAME_PATTERN + ")" + ":" + "(?:[0-9]{1,5})"
    PRIORITY_PATTERN = "(?P<priority>!-?\d+)?"
    DB_NAME = re.compile("^" + DB_NAME_PATTERN + PRIORITY_PATTERN + "$")
    URL = re.compile("^" + URL_PATTERN + PRIORITY_PATTERN + "$")
    URL_DB_NAME = re.compile("^(?P<url>" + URL_PATTERN + ")" + ":" +
                             "(?P<db_name>" + DB_NAME_PATTERN + ")" +
                             PRIORITY_PATTERN + "$")

    @classmethod
    def apply(cls, args, run):
        url, db_name, collection, priority = cls.parse_mongo_db_arg(args)
        if collection:
            mongo = MongoObserver.create(db_name=db_name, url=url,
                                         collection=collection,
                                         priority=priority)
        else:
            mongo = MongoObserver.create(db_name=db_name, url=url,
                                         priority=priority)

        run.observers.append(mongo)

    @classmethod
    def parse_mongo_db_arg(cls, mongo_db):
        def get_priority(pattern):
            prio_str = pattern.match(mongo_db).group('priority')
            if prio_str is None:
                return DEFAULT_MONGO_PRIORITY
            else:
                return int(prio_str[1:])

        if cls.DB_NAME.match(mongo_db):
            db_name, _, collection = mongo_db.partition('.')
            return ('localhost:27017', db_name, collection,
                    get_priority(cls.DB_NAME))
        elif cls.URL.match(mongo_db):
            return mongo_db, 'sacred', '', get_priority(cls.URL)
        elif cls.URL_DB_NAME.match(mongo_db):
            match = cls.URL_DB_NAME.match(mongo_db)
            db_name, _, collection = match.group('db_name').partition('.')
            return (match.group('url'), db_name, collection,
                    get_priority(cls.URL_DB_NAME))
        else:
            raise ValueError('mongo_db argument must have the form "db_name" '
                             'or "host:port[:db_name]" but was {}'
                             .format(mongo_db))
