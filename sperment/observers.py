#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
import pickle
import time

import numpy as np
from pymongo import MongoClient
from pymongo.son_manipulator import SONManipulator
from bson import Binary


class ExperimentObserver(object):
    def experiment_created_event(self, name, stages, seed, mainfile, doc):
        pass

    def experiment_started_event(self, name, mainfile, doc, start_time, config,
                                 info):
        pass

    def experiment_info_updated(self, info):
        pass

    def experiment_completed_event(self, stop_time, result, info):
        pass

    def experiment_interrupted_event(self, interrupt_time, info):
        pass

    def experiment_failed_event(self, fail_time, info):
        pass


class PickleNumpyArrays(SONManipulator):
    """
    Helper that makes sure numpy arrays get pickled and stored in the database
    as binary strings.
    """
    def transform_incoming(self, son, collection):
        for (key, value) in son.items():
            if isinstance(value, np.ndarray):
                son[key] = {"_type": "ndarray",
                            "_value": Binary(pickle.dumps(value, protocol=2))}
            elif isinstance(value, dict):  # Make sure we recurse into sub-docs
                son[key] = self.transform_incoming(value, collection)
        return son

    def transform_outgoing(self, son, collection):
        for (key, value) in son.items():
            if isinstance(value, dict):
                if "_type" in value and value["_type"] == "ndarray":
                    son[key] = pickle.loads(str(value["_value"]))
                else:  # Again, make sure to recurse into sub-docs
                    son[key] = self.transform_outgoing(value, collection)
        return son


class MongoDBReporter(ExperimentObserver):
    def __init__(self, url=None, db_name='sperment', save_delay=1):
        super(MongoDBReporter, self).__init__()
        self.experiment_entry = None
        self.last_save = 0
        self.save_delay = save_delay
        mongo = MongoClient(url)
        self.db = mongo[db_name]
        self.db.add_son_manipulator(PickleNumpyArrays())
        self.collection = self.db['experiments']

    def save(self):
        self.last_save = time.time()
        self.collection.save(self.experiment_entry)

    def experiment_started_event(self, name, mainfile, doc, start_time, config,
                                 info):
        self.experiment_entry = dict()
        self.experiment_entry['name'] = name
        self.experiment_entry['mainfile'] = mainfile
        self.experiment_entry['doc'] = doc
        self.experiment_entry['start_time'] = start_time
        self.experiment_entry['config'] = config
        self.experiment_entry['info'] = info
        self.experiment_entry['status'] = 'RUNNING'
        self.save()

    def experiment_info_updated(self, info):
        self.experiment_entry['info'] = info
        if time.time() >= self.last_save + self.save_delay:
            self.save()

    def experiment_completed_event(self, stop_time, result, info):
        self.experiment_entry['stop_time'] = stop_time
        self.experiment_entry['result'] = result
        self.experiment_entry['info'] = info
        self.experiment_entry['status'] = 'COMPLETED'
        self.save()

    def experiment_interrupted_event(self, interrupt_time, info):
        self.experiment_entry['stop_time'] = interrupt_time
        self.experiment_entry['info'] = info
        self.experiment_entry['status'] = 'INTERRUPTED'
        self.save()

    def experiment_failed_event(self, fail_time, info):
        self.experiment_entry['stop_time'] = fail_time
        self.experiment_entry['info'] = info
        self.experiment_entry['status'] = 'FAILED'
        self.save()

    def __eq__(self, other):
        if not isinstance(other, MongoDBReporter):
            return False
        return self.collection == other.collection

    def __ne__(self, other):
        return not self.__eq__(other)
