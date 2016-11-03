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
from tinydb_serialization import Serializer, SerializationMiddleware

from hashfs import HashFS


class DateTimeSerializer(Serializer):
    OBJ_CLASS = dt.datetime  # The class this serializer handles

    def encode(self, obj):
        return obj.strftime('%Y-%m-%dT%H:%M:%S.%f')

    def decode(self, s):
        return dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')


class NdArraySerializer(Serializer):
    OBJ_CLASS = opt.np.ndarray 

    def encode(self, obj):
        return json.dumps(obj.tolist(), check_circular=True)

    def decode(self, s):
        return opt.np.array(json.loads(s))


class DataFrameSerializer(Serializer):
    OBJ_CLASS = opt.pandas.DataFrame 

    def encode(self, obj):
        return obj.to_json()

    def decode(self, s):
        return opt.pandas.read_json(s)


class SeriesSerializer(Serializer):
    OBJ_CLASS = opt.pandas.core.series.Series  

    def encode(self, obj):
        return obj.to_json()

    def decode(self, s):
        return opt.pandas.read_json(s, typ='series')


class TinyDbObserver(RunObserver):

    VERSION = "TinyDbObserver-{}".format(__version__)

    @staticmethod 
    def create(path='.', name='observer_db', overwrite=None):

        location = os.path.abspath(path)
        root_dir = os.path.join(location, name)
        if not os.path.exists(root_dir):
            os.makedirs(root_dir)

        # Setup Serialisation object for non list/dict objects 
        serialization_store = SerializationMiddleware()
        serialization_store.register_serializer(DateTimeSerializer(), 'TinyDate')
        serialization_store.register_serializer(NdArraySerializer(), 'TinyArray')
        serialization_store.register_serializer(DataFrameSerializer(), 'TinyDataFrame')
        serialization_store.register_serializer(SeriesSerializer(), 'TinySeries')

        db = TinyDB(os.path.join(root_dir, 'metadata.json'), storage=serialization_store)
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
        
        source_info = []
        for source_name, md5 in ex_info['sources']:
        
            file = self.fs.get(md5)
            if file:
                id_ = file.id
            else:
                # Substitute any HOME or Environment Vars to get absolute path
                abs_path = os.path.expanduser(source_name)
                abs_path = os.path.expandvars(source_name)
                address = self.fs.put(abs_path)
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
        resource = (filename, md5hash)
        
        if file_:
            if resource not in self.run_entry['resources']:
                self.run_entry['resources'].append(resource)
                self.save()
        else: 
            self.fs.put(filename)
            self.run_entry['resources'].append((filename, md5hash))
            self.save()

    def artifact_event(self, name, filename):

        md5hash = get_digest(filename)

        self.fs.put(filename)
        self.run_entry['artifacts'].append({'name': name,
                                            'file_id': md5hash})
        self.save()

    def __eq__(self, other):
        if isinstance(other, TinyDbObserver):
            return self.runs.all() == other.runs.all()
        return False

    def __ne__(self, other):
        return not self.__eq__(other)
