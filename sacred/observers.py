#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from datetime import datetime
import os.path
import pickle
import sys
import time
from sacred.dependencies import get_digest

__sacred__ = True  # marks files that should be filtered from stack traces

__all__ = ['RunObserver', 'MongoObserver', 'DebugObserver']


class RunObserver(object):
    def started_event(self, name, ex_info, host_info, start_time, config):
        pass

    def heartbeat_event(self, info, captured_out):
        pass

    def completed_event(self, stop_time, result):
        pass

    def interrupted_event(self, interrupt_time):
        pass

    def failed_event(self, fail_time, fail_trace):
        pass

    def resource_event(self, filename):
        pass

    def artifact_event(self, filename):
        pass


try:
    from pymongo import MongoClient
    from pymongo.errors import AutoReconnect
    from pymongo.son_manipulator import SONManipulator
    from bson import Binary
    import gridfs

    SON_MANIPULATORS = []

    try:
        import numpy as np

        class PickleNumpyArrays(SONManipulator):
            """
            Helper that makes sure numpy arrays get pickled and stored in the
            database as binary strings.
            """
            def transform_incoming(self, son, collection):
                for (key, value) in son.items():
                    if isinstance(value, np.ndarray):
                        son[key] = {
                            "_type": "ndarray",
                            "_value": Binary(pickle.dumps(value, protocol=2))}
                    elif isinstance(value, dict):
                        # Make sure we recurse into sub-docs
                        son[key] = self.transform_incoming(value, collection)
                return son

            def transform_outgoing(self, son, collection):
                for (key, value) in son.items():
                    if isinstance(value, dict):
                        if "_type" in value and value["_type"] == "ndarray":
                            son[key] = pickle.loads(str(value["_value"]))
                        else:  # Again, make sure to recurse into sub-docs
                            son[key] = self.transform_outgoing(value,
                                                               collection)
                return son

        SON_MANIPULATORS.append(PickleNumpyArrays())
    except ImportError:
        pass

    class MongoObserver(RunObserver):
        @staticmethod
        def create(url, db_name='sacred', **kwargs):
            client = MongoClient(url, **kwargs)
            database = client[db_name]
            for manipulator in SON_MANIPULATORS:
                database.add_son_manipulator(manipulator)
            experiments_collection = database['experiments']
            fs = gridfs.GridFS(database)
            return MongoObserver(experiments_collection, fs)

        def __init__(self, experiments_collection, fs):
            self.collection = experiments_collection
            self.fs = fs
            self.experiment_entry = None

        def save(self):
            try:
                self.collection.save(self.experiment_entry)
            except AutoReconnect:  # just wait for the next save
                pass

        def final_save(self, attempts=10):
            for i in range(attempts):
                try:
                    self.collection.save(self.experiment_entry)
                    return
                except AutoReconnect:
                    if i < attempts - 1:
                        time.sleep(1)

            from tempfile import NamedTemporaryFile
            with NamedTemporaryFile(suffix='.pickle', delete=False,
                                    prefix='sacred_mongo_fail_') as f:
                pickle.dump(self.experiment_entry, f)
                print("Warning: saving to MongoDB failed! "
                      "Stored experiment entry in '%s'" % f.name,
                      file=sys.stderr)

        def started_event(self, name, ex_info, host_info, start_time, config):
            self.experiment_entry = dict()
            self.experiment_entry['name'] = name
            self.experiment_entry['experiment_info'] = ex_info
            self.experiment_entry['host_info'] = host_info
            self.experiment_entry['start_time'] = \
                datetime.fromtimestamp(start_time)
            self.experiment_entry['config'] = config
            self.experiment_entry['status'] = 'RUNNING'
            self.experiment_entry['resources'] = []
            self.experiment_entry['artifacts'] = []
            self.save()

            for source_name, md5 in ex_info['sources']:
                if not self.fs.exists(filename=source_name, md5=md5):
                    with open(source_name, 'rb') as f:
                        self.fs.put(f, filename=source_name)

        def heartbeat_event(self, info, captured_out):
            self.experiment_entry['info'] = info
            self.experiment_entry['captured_out'] = captured_out
            self.experiment_entry['heartbeat'] = datetime.now()
            self.save()

        def completed_event(self, stop_time, result):
            self.experiment_entry['stop_time'] = \
                datetime.fromtimestamp(stop_time)
            self.experiment_entry['result'] = result
            self.experiment_entry['status'] = 'COMPLETED'
            self.final_save(attempts=10)

        def interrupted_event(self, interrupt_time):
            self.experiment_entry['stop_time'] = \
                datetime.fromtimestamp(interrupt_time)
            self.experiment_entry['status'] = 'INTERRUPTED'
            self.final_save(attempts=3)

        def failed_event(self, fail_time, fail_trace):
            self.experiment_entry['stop_time'] = \
                datetime.fromtimestamp(fail_time)
            self.experiment_entry['status'] = 'FAILED'
            self.experiment_entry['fail_trace'] = fail_trace
            self.final_save(attempts=1)

        def resource_event(self, filename):
            if self.fs.exists(filename=filename):
                md5hash = get_digest(filename)
                if self.fs.exists(filename=filename, md5=md5hash):
                    resource = (filename, md5hash)
                    if resource not in self.experiment_entry['resources']:
                        self.experiment_entry['resources'].append(resource)
                    return
            with open(filename, 'rb') as f:
                file_id = self.fs.put(f, filename=filename)
            md5hash = self.fs.get(file_id).md5
            self.experiment_entry['resources'].append((filename, md5hash))

        def artifact_event(self, filename):
            with open(filename, 'rb') as f:
                head, tail = os.path.split(filename)
                run_id = self.experiment_entry['_id']
                db_filename = 'artifact://{}/{}/{}'.format(
                    self.experiment_entry['name'], run_id, tail)
                file_id = self.fs.put(f, filename=db_filename)
            self.experiment_entry['artifacts'].append(file_id)
            self.save()

        def __eq__(self, other):
            if isinstance(other, MongoObserver):
                return self.collection == other.collection
            return False

        def __ne__(self, other):
            return not self.__eq__(other)

except ImportError:
    class MongoObserver(RunObserver):
        @staticmethod
        def create(url, db_name='sacred', **kwargs):
            raise ImportError('only available if "pymongo" is installed')

        def __init__(self, experiments_collection, sources_fs):
            raise ImportError('only available if "pymongo" is installed')


class DebugObserver(RunObserver):
    def started_event(self, name, ex_info, host_info, start_time, config):
        print('experiment_started_event')

    def heartbeat_event(self, info, captured_out):
        print('experiment_info_updated')

    def completed_event(self, stop_time, result):
        print('experiment_completed_event')

    def interrupted_event(self, interrupt_time):
        print('experiment_interrupted_event')

    def failed_event(self, fail_time, fail_trace):
        print('experiment_failed_event')

    def resource_event(self, filename):
        print('resource_event: {}'.format(filename))

    def artifact_event(self, filename):
        print('artifact_event: {}'.format(filename))
