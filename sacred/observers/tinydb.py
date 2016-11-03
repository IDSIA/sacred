#!/usr/bin/env python
# coding=utf-8
import os
import datetime as dt 
import json
import uuid

from sacred.__about__ import __version__
from sacred.observers import RunObserver
from sacred.dependencies import get_digest
import sacred.optional as opt

from tinydb import TinyDB
from tinydb.middlewares import Middleware
from tinydb.storages import JSONStorage
from tinydb_serialization import Serializer, SerializationMiddleware

from hashfs import HashFS


class DateTimeSerializer(Serializer):
    OBJ_CLASS = dt.datetime  # The class this serializer handles

    def encode(self, obj):
        return obj.strftime('%Y-%m-%dT%H:%M:%S')

    def decode(self, s):
        return dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')


class NdArraySerializer(Serializer):
    OBJ_CLASS = opt.np.ndarray  # The class this serializer handles

    def encode(self, obj):
        return json.dumps(obj.tolist(), check_circular=True)

    def decode(self, s):
        return opt.np.array(json.loads(s))


class DataFrameSerializer(Serializer):
    OBJ_CLASS = opt.pandas.DataFrame  # The class this serializer handles

    def encode(self, obj):
        return obj.to_json()

    def decode(self, s):
        return opt.pandas.read_json(s)


class TinyDbObserver(RunObserver):

    VERSION = "TinyDbObserver-{}".format(__version__)

    @staticmethod 
    def create(path='.', name='observer_db', overwrite=None):

        location = os.path.abspath(path)
        root_dir = os.path.join(location, name)
        if not os.path.exists(root_dir):
            os.makedirs(root_dir)

        # Setup Serialisation of non list/dict objects 
        serialization = SerializationMiddleware()
        serialization.register_serializer(DateTimeSerializer(), 'TinyDate')
        serialization.register_serializer(NdArraySerializer(), 'TinyArray')
        serialization.register_serializer(DataFrameSerializer(), 'TinyDataFrame')

        db = TinyDB(os.path.join(root_dir, 'metadata.json'), storage=serialization)
        fs = HashFS(os.path.join(root_dir, 'hashfs'), depth=3, width=2, algorithm='md5')

        return TinyDbObserver(db, fs, overwrite=overwrite)

    def __init__(self, db, fs, overwrite=None):
        self.db = db
        self.runs = db.table('runs')
        self.fs = fs
        self.overwrite = overwrite
        self.run_entry = {}
        self.db_run_id = None

    def save(self):
        """ Insert or update the current entry """
        if self.db_run_id:
            self.runs.update(self.run_entry, eids=[self.db_run_id])
        else:
            db_run_id = self.runs.insert(self.run_entry)
            self.db_run_id = db_run_id

    def save_sources(self, ex_info):
        
        # base_dir = ex_info['base_dir']
        source_info = []
        for source_name, md5 in ex_info['sources']:
        
            file = self.fs.get(md5)
            if file:
                id_ = file.id
            else:
                # Substitute any HOME or Environment Vars to get absolute path
                abs_path = os.path.expanduser(source_name)
                abs_path = os.path.expandvars(source_name)
                with open(abs_path, 'rb') as f:
                    address = self.fs.put(f)
                    id_ = address.id
            source_info.append([source_name, id_])
        return source_info

    def queued_event(self, ex_info, command, queue_time, config, meta_info,
                     _id):
        raise NotImplementedError('queued_event method is not implimented for local TinyDbObserver.')

    def started_event(self, ex_info, command, host_info, start_time, config,
                      meta_info, _id):

        self.run_entry = {
            'experiment': dict(ex_info),
            'format': self.VERSION,
            'command': command,
            'host': dict(host_info),
            'start_time': start_time,
            'config': config,
            'meta': meta_info,
            'status': 'RUNNING',
            'resources': [],
            'artifacts': [],
            'captured_out': '',
            'info': {},
            'heartbeat': None
        }

        # set ID if not given
        if _id is None:
            _id = uuid.uuid4().hex

        self.run_entry['_id'] = _id
        
        # save sources
        self.run_entry['experiment']['sources'] = self.save_sources(ex_info)
        self.save()
        return self.run_entry['_id']

    def heartbeat_event(self, info, cout_filename, beat_time):
        self.run_entry['info'] = info
        with open(cout_filename, 'r') as f:
            self.run_entry['captured_out'] = f.read()
        self.run_entry['heartbeat'] = beat_time
        self.save()

    def completed_event(self, stop_time, result):
        self.run_entry['stop_time'] = stop_time
        self.run_entry['result'] = result
        self.run_entry['status'] = 'COMPLETED'
        self.save()

    def interrupted_event(self, interrupt_time, status):
        self.run_entry['stop_time'] = interrupt_time
        self.run_entry['status'] = status
        self.save()

    def failed_event(self, fail_time, fail_trace):
        self.run_entry['stop_time'] = fail_time
        self.run_entry['status'] = 'FAILED'
        self.run_entry['fail_trace'] = fail_trace
        self.save()

    def resource_event(self, filename):

        md5hash = get_digest(filename)
        file_ = self.fs.get(md5hash)

        if file_:
            resource = (filename, md5hash)
            if resource not in self.run_entry['resources']:
                self.run_entry['resources'].append(resource)
                self.save()
        else: 
            self.fs.put(filename)
            self.run_entry['resources'].append((filename, md5hash))
            self.save()

    def artifact_event(self, filename):

        md5hash = get_digest(filename)
        file_ = self.fs.get(md5hash)

        if file_:
            artifact = (filename, md5hash)
            if artifact not in self.run_entry['artifacts']:
                self.run_entry['artifacts'].append(artifact)
                self.save()
        else: 
            self.fs.put(filename)
            self.run_entry['artifacts'].append((filename, md5hash))
            self.save()

    def __eq__(self, other):
        if isinstance(other, TinyDbObserver):
            return self.runs == other.runs
        return False

    def __ne__(self, other):
        return not self.__eq__(other)


# class SerializeArrayDataFrameMiddleware(Middleware):

#     """ Custom Middleware to handle arrays and DataFrame serialisation """
    
#     def __init__(self, storage_cls=TinyDB.DEFAULT_STORAGE):
#         # Any middleware *has* to call the super constructor
#         # with storage_cls
#         super(SerializeArrayDataFrameMiddleware, self).__init__(storage_cls)

#     def read(self):
#         data = self.storage.read()

#         return data

#     def write(self, data):

#         for table_name in data:
#             table = data[table_name]

#             for element_id in table:
#                 doc = table[element_id]
#                 doc = self._convert(doc)

#         self.storage.write(data)

#     def _convert(self, doc):
#         """ Recursively convert array and DataFrame to lists/json """
#         for key, value in doc.items():
#             if isinstance(value, (opt.pandas.Series, opt.pandas.DataFrame, opt.pandas.Panel)):
#                 doc[key] = value.to_json()
#             elif isinstance(value, opt.np.ndarray):
#                 doc[key] = value.tolist()
#             elif isinstance(value, dt.datetime):
#                 doc[key] = value.isoformat()
#             elif isinstance(value, dict):
#                 # Make sure we recurse into sub-docs
#                 doc[key] = self._convert(value)
#         return doc

#     def close(self):
#         self.storage.close()