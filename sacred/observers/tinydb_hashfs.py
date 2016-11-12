#!/usr/bin/env python
# coding=utf-8
from __future__ import (division, print_function, unicode_literals,
                        absolute_import)

import os
import datetime as dt
import json
import uuid

from io import BufferedReader

from sacred.__about__ import __version__
from sacred.observers import RunObserver
from sacred.commandline_options import CommandLineOption
import sacred.optional as opt

from tinydb import TinyDB
from hashfs import HashFS
from tinydb_serialization import Serializer, SerializationMiddleware

__sacred__ = True  # marks files that should be filtered from stack traces

# Set data type values for abstract properties in Serializers
series_type = opt.pandas.Series if opt.has_pandas else None
dataframe_type = opt.pandas.DataFrame if opt.has_pandas else None
ndarray_type = opt.np.ndarray if opt.has_numpy else None


class BufferedReaderWrapper(BufferedReader):

    """Custom wrapper to allow for copying of file handle.

    tinydb_serialisation currently does a deepcopy on all the content of the 
    dictionary before serialisation. By default, file handles are not 
    copiable so this wrapper is necessary to create a duplicate of the 
    file handle passes in.  

    Note that the file passed in will therefor remain open as the copy is the
    one thats closed.
    """

    def __init__(self, *args, **kwargs):
        super(BufferedReaderWrapper, self).__init__(*args, **kwargs)

    def __copy__(self):
        f = open(self.name, self.mode)
        return BufferedReaderWrapper(f)

    def __deepcopy__(self, memo):
        f = open(self.name, self.mode)
        return BufferedReaderWrapper(f)


class DateTimeSerializer(Serializer):
    OBJ_CLASS = dt.datetime  # The class this serializer handles

    def encode(self, obj):
        return obj.strftime('%Y-%m-%dT%H:%M:%S.%f')

    def decode(self, s):
        return dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')


class NdArraySerializer(Serializer):
    OBJ_CLASS = ndarray_type

    def encode(self, obj):
        return json.dumps(obj.tolist(), check_circular=True)

    def decode(self, s):
        return opt.np.array(json.loads(s))


class DataFrameSerializer(Serializer):
    OBJ_CLASS = dataframe_type

    def encode(self, obj):
        return obj.to_json()

    def decode(self, s):
        return opt.pandas.read_json(s)


class SeriesSerializer(Serializer):
    OBJ_CLASS = series_type

    def encode(self, obj):
        return obj.to_json()

    def decode(self, s):
        return opt.pandas.read_json(s, typ='series')


class FileSerializer(Serializer):
    OBJ_CLASS = BufferedReaderWrapper

    def __init__(self, fs):
        self.fs = fs

    def encode(self, obj):
        address = self.fs.put(obj)
        return json.dumps(address.id)

    def decode(self, s):
        id_ = json.loads(s)
        file_reader = self.fs.open(id_)
        file_reader = BufferedReaderWrapper(file_reader)
        file_reader.hash = id_
        return file_reader


class TinyDbObserver(RunObserver):

    VERSION = "TinyDbObserver-{}".format(__version__)

    @staticmethod
    def create(path='./runs_db', overwrite=None):

        root_dir = os.path.abspath(path)
        if not os.path.exists(root_dir):
            os.makedirs(root_dir)

        fs = HashFS(os.path.join(root_dir, 'hashfs'), depth=3,
                    width=2, algorithm='md5')

        # Setup Serialisation object for non list/dict objects
        serialization_store = SerializationMiddleware()
        serialization_store.register_serializer(DateTimeSerializer(),
                                                'TinyDate')
        serialization_store.register_serializer(FileSerializer(fs),
                                                'TinyFile')

        if opt.has_numpy:
            serialization_store.register_serializer(NdArraySerializer(),
                                                    'TinyArray')
        if opt.has_pandas:
            serialization_store.register_serializer(DataFrameSerializer(),
                                                    'TinyDataFrame')
            serialization_store.register_serializer(SeriesSerializer(),
                                                    'TinySeries')

        db = TinyDB(os.path.join(root_dir, 'metadata.json'),
                    storage=serialization_store)

        return TinyDbObserver(db, fs, overwrite=overwrite)

    def __init__(self, db, fs, overwrite=None):
        self.db = db
        self.runs = db.table('runs')
        self.fs = fs
        self.overwrite = overwrite
        self.run_entry = {}
        self.db_run_id = None

    def save(self):
        """Insert or update the current run entry."""
        if self.db_run_id:
            self.runs.update(self.run_entry, eids=[self.db_run_id])
        else:
            print(self.run_entry)
            db_run_id = self.runs.insert(self.run_entry)
            self.db_run_id = db_run_id

    def save_sources(self, ex_info):

        source_info = []
        for source_name, md5 in ex_info['sources']:

            # Substitute any HOME or Environment Vars to get absolute path
            abs_path = os.path.expanduser(source_name)
            abs_path = os.path.expandvars(source_name)
            handle = BufferedReaderWrapper(open(abs_path, 'rb'))

            file = self.fs.get(md5)
            if file:
                id_ = file.id                
            else:
                address = self.fs.put(abs_path)
                id_ = address.id
            source_info.append([source_name, id_, handle])
        return source_info

    def queued_event(self, ex_info, command, queue_time, config, meta_info,
                     _id):
        raise NotImplementedError('queued_event method is not implimented for'
                                  ' local TinyDbObserver.')

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

        id_ = self.fs.put(filename).id
        handle = BufferedReaderWrapper(open(filename, 'rb'))        
        resource = [filename, id_, handle]

        if resource not in self.run_entry['resources']:
            self.run_entry['resources'].append(resource)
            self.save()

    def artifact_event(self, name, filename):

        id_ = self.fs.put(filename).id
        handle = BufferedReaderWrapper(open(filename, 'rb'))        
        artifact = [name, filename, id_, handle]
        
        if artifact not in self.run_entry['artifacts']:
            self.run_entry['artifacts'].append(artifact)
            self.save()

    def __eq__(self, other):
        if isinstance(other, TinyDbObserver):
            return self.runs.all() == other.runs.all()
        return False

    def __ne__(self, other):
        return not self.__eq__(other)


class TinyDbOption(CommandLineOption):
    """Add a TinyDB Observer to the experiment."""

    arg = 'BASEDIR'

    @classmethod
    def apply(cls, args, run):
        location = cls.parse_tinydb_arg(args)
        tinydb_obs = TinyDbObserver.create(path=location)
        run.observers.append(tinydb_obs)

    @classmethod
    def parse_tinydb_arg(cls, args):
        return args
