#!/usr/bin/env python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from datetime import datetime
import pickle

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


try:
    from pymongo import MongoClient
    from pymongo.son_manipulator import SONManipulator
    from bson import Binary

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
        def __init__(self, url=None, db_name='sacred'):
            RunObserver.__init__(self)
            self.experiment_entry = None
            mongo = MongoClient(url)
            database = mongo[db_name]
            for manipulator in SON_MANIPULATORS:
                database.add_son_manipulator(manipulator)
            self.collection = database['experiments']

        def save(self):
            self.collection.save(self.experiment_entry)

        def started_event(self, name, ex_info, host_info, start_time, config):
            self.experiment_entry = dict()
            self.experiment_entry['name'] = name
            self.experiment_entry['experiment_info'] = ex_info
            try:
                with open(ex_info['mainfile']) as source_file:
                    self.experiment_entry['source'] = source_file.read()
            except IOError as err:
                self.experiment_entry['experiment_info']['source'] = str(err)
            self.experiment_entry['host_info'] = host_info
            self.experiment_entry['start_time'] = \
                datetime.fromtimestamp(start_time)
            self.experiment_entry['config'] = config
            self.experiment_entry['status'] = 'RUNNING'
            self.save()

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
            self.save()

        def interrupted_event(self, interrupt_time):
            self.experiment_entry['stop_time'] = \
                datetime.fromtimestamp(interrupt_time)
            self.experiment_entry['status'] = 'INTERRUPTED'
            self.save()

        def failed_event(self, fail_time, fail_trace):
            self.experiment_entry['stop_time'] = \
                datetime.fromtimestamp(fail_time)
            self.experiment_entry['status'] = 'FAILED'
            self.experiment_entry['fail_trace'] = fail_trace
            self.save()

        def __eq__(self, other):
            if isinstance(other, MongoObserver):
                return self.collection == other.collection
            return False

        def __ne__(self, other):
            return not self.__eq__(other)

except ImportError:
    class MongoObserver(RunObserver):
        def __init__(self, url=None, db_name='sacred'):
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
