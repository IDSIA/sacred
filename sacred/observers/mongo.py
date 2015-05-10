#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import os.path
import pickle
import sys
import time

import bson
import gridfs
import pymongo
import sacred.optional as opt
from pymongo.errors import AutoReconnect, InvalidDocument
from pymongo.son_manipulator import SONManipulator
from sacred.dependencies import get_digest
from sacred.observers.base import RunObserver
from sacred.utils import ObserverError

SON_MANIPULATORS = []


class PickleNumpyArrays(SONManipulator):

    """Make sure numpy arrays get pickled and stored as binary strings."""

    def transform_incoming(self, son, collection):
        for (key, value) in son.items():
            if isinstance(value, opt.np.ndarray):
                son[key] = {
                    "_type": "ndarray",
                    "_value": bson.Binary(pickle.dumps(value, protocol=2))
                }
            elif isinstance(value, dict):
                # Make sure we recurse into sub-docs
                son[key] = self.transform_incoming(value, collection)
        return son

    def transform_outgoing(self, son, collection):
        for (key, value) in son.items():
            if isinstance(value, dict):
                if "_type" in value and value["_type"] == "ndarray":
                    son[key] = pickle.loads(value["_value"])
                else:  # Again, make sure to recurse into sub-docs
                    son[key] = self.transform_outgoing(value, collection)
        return son


if opt.has_numpy:
    SON_MANIPULATORS.append(PickleNumpyArrays())


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
    @staticmethod
    def create(url='localhost', db_name='sacred', prefix='default', **kwargs):
        client = pymongo.MongoClient(url, **kwargs)
        database = client[db_name]
        for manipulator in SON_MANIPULATORS:
            database.add_son_manipulator(manipulator)
        runs_collection = database[prefix + '.runs']
        fs = gridfs.GridFS(database, collection=prefix)
        return MongoObserver(runs_collection, fs)

    def __init__(self, runs_collection, fs):
        self.runs = runs_collection
        self.fs = fs
        self.run_entry = None

    def save(self):
        try:
            self.runs.save(self.run_entry)
        except AutoReconnect:
            pass  # just wait for the next save
        except InvalidDocument:
            raise ObserverError('Run contained an unserializable entry.'
                                '(most likely in the info)')

    def final_save(self, attempts=10):
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
                  "Stored experiment entry in '%s'" % f.name,
                  file=sys.stderr)

    def started_event(self, ex_info, host_info, start_time, config):
        self.run_entry = {
            'experiment': dict(ex_info),
            'host': dict(host_info),
            'start_time': start_time,
            'config': config,
            'status': 'RUNNING',
            'resources': [],
            'artifacts': [],
            'captured_out': '',
            'info': {},
            'heartbeat': None
        }

        self.save()
        for source_name, md5 in ex_info['sources']:
            if not self.fs.exists(filename=source_name, md5=md5):
                with open(source_name, 'rb') as f:
                    self.fs.put(f, filename=source_name)

    def heartbeat_event(self, info, captured_out, beat_time):
        self.run_entry['info'] = info
        self.run_entry['captured_out'] = captured_out
        self.run_entry['heartbeat'] = beat_time
        self.save()

    def completed_event(self, stop_time, result):
        self.run_entry['stop_time'] = stop_time
        self.run_entry['result'] = result
        self.run_entry['status'] = 'COMPLETED'
        self.final_save(attempts=10)

    def interrupted_event(self, interrupt_time):
        self.run_entry['stop_time'] = interrupt_time
        self.run_entry['status'] = 'INTERRUPTED'
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

    def artifact_event(self, filename):
        with open(filename, 'rb') as f:
            head, tail = os.path.split(filename)
            run_id = self.run_entry['_id']
            db_filename = 'artifact://{}/{}/{}'.format(
                self.run_entry['experiment']['name'], run_id, tail)
            file_id = self.fs.put(f, filename=db_filename)
        self.run_entry['artifacts'].append(file_id)
        self.save()

    def __eq__(self, other):
        if isinstance(other, MongoObserver):
            return self.runs == other.runs
        return False

    def __ne__(self, other):
        return not self.__eq__(other)
