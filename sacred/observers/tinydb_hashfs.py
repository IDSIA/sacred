#!/usr/bin/env python
# coding=utf-8
from __future__ import (division, print_function, unicode_literals,
                        absolute_import)

import os
import datetime as dt
import json
import uuid
import textwrap
from collections import OrderedDict

from io import BufferedReader, FileIO

from sacred.__about__ import __version__
from sacred.observers import RunObserver
from sacred.commandline_options import CommandLineOption
import sacred.optional as opt

from tinydb import TinyDB, Query
from tinydb.queries import QueryImpl
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
    one that gets closed.
    """

    def __init__(self, f_obj):
        f_obj = FileIO(f_obj.name)
        super(BufferedReaderWrapper, self).__init__(f_obj)

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

        return TinyDbObserver(db, fs, overwrite=overwrite, root=root_dir)

    def __init__(self, db, fs, overwrite=None, root=None):
        self.db = db
        self.runs = db.table('runs')
        self.fs = fs
        self.overwrite = overwrite
        self.run_entry = {}
        self.db_run_id = None
        self.root = root

    def save(self):
        """Insert or update the current run entry."""
        if self.db_run_id:
            self.runs.update(self.run_entry, eids=[self.db_run_id])
        else:
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

    def heartbeat_event(self, info, captured_out, beat_time):
        self.run_entry['info'] = info
        self.run_entry['captured_out'] = captured_out
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


class TinyDbReader(object):

    def __init__(self, path):

        root_dir = os.path.abspath(path)
        if not os.path.exists(root_dir):
            raise IOError('Path does not exist: %s' % path)

        fs = HashFS(os.path.join(root_dir, 'hashfs'), depth=3,
                    width=2, algorithm='md5')

        # Setup Serialisation for non list/dict objects
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

        self.db = db
        self.runs = db.table('runs')
        self.fs = fs

    def search(self, *args, **kwargs):
        """Wrapper to TinyDB's search function."""
        return self.runs.search(*args, **kwargs)

    def fetch_files(self, exp_name=None, query=None, indices=None):
        """Return Dictionary of files for experiment name or query.

        Returns a list of one dictionary per matched experiment. The
        dictionary is of the following structure

            {
              'exp_name': 'scascasc',
              'exp_id': 'dqwdqdqwf',
              'date': datatime_object,
              'sources': [ {'filename': filehandle}, ..., ],
              'resources': [ {'filename': filehandle}, ..., ],
              'artifacts': [ {'filename': filehandle}, ..., ]
            }

        """
        entries = self.fetch_metadata(exp_name, query, indices)

        all_matched_entries = []
        for ent in entries:

            rec = dict(exp_name=ent['experiment']['name'],
                       exp_id=ent['_id'],
                       date=ent['start_time'])

            source_files = {x[0]: x[2] for x in ent['experiment']['sources']}
            resource_files = {x[0]: x[2] for x in ent['resources']}
            artifact_files = {x[0]: x[3] for x in ent['artifacts']}

            if source_files:
                rec['sources'] = source_files
            if resource_files:
                rec['resources'] = resource_files
            if artifact_files:
                rec['artifacts'] = artifact_files

            all_matched_entries.append(rec)

        return all_matched_entries

    def fetch_report(self, exp_name=None, query=None, indices=None):

        template = """
-------------------------------------------------
Experiment: {exp_name}
-------------------------------------------------
ID: {exp_id}
Date: {start_date}    Duration: {duration}

Parameters:
{parameters}

Result:
{result}

Dependencies:
{dependencies}

Resources:
{resources}

Source Files:
{sources}

Outputs:
{artifacts}
"""

        entries = self.fetch_metadata(exp_name, query, indices)

        all_matched_entries = []
        for ent in entries:

            date = ent['start_time']
            weekdays = 'Mon Tue Wed Thu Fri Sat Sun'.split()
            w = weekdays[date.weekday()]
            date = ' '.join([w, date.strftime('%d %b %Y')])

            duration = ent['stop_time'] - ent['start_time']
            secs = duration.total_seconds()
            hours, remainder = divmod(secs, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration = '%02d:%02d:%04.1f' % (hours, minutes, seconds)

            parameters = self._dict_to_indented_list(ent['config'])

            result = self._indent(ent['result'].__repr__(), prefix='    ')

            deps = ent['experiment']['dependencies']
            deps = self._indent('\n'.join(deps), prefix='    ')

            resources = [x[0] for x in ent['resources']]
            resources = self._indent('\n'.join(resources), prefix='    ')

            sources = [x[0] for x in ent['experiment']['sources']]
            sources = self._indent('\n'.join(sources), prefix='    ')

            artifacts = [x[0] for x in ent['artifacts']]
            artifacts = self._indent('\n'.join(artifacts), prefix='    ')

            none_str = '    None'

            rec = dict(exp_name=ent['experiment']['name'],
                       exp_id=ent['_id'],
                       start_date=date,
                       duration=duration,
                       parameters=parameters if parameters else none_str,
                       result=result if result else none_str,
                       dependencies=deps if deps else none_str,
                       resources=resources if resources else none_str,
                       sources=sources if sources else none_str,
                       artifacts=artifacts if artifacts else none_str)

            report = template.format(**rec)

            all_matched_entries.append(report)

        return all_matched_entries

    def fetch_metadata(self, exp_name=None, query=None, indices=None):
        """Return all metadata for matching experiment name, index or query."""
        if exp_name or query:
            if query:
                assert type(query), QueryImpl
                q = query
            elif exp_name:
                q = Query().experiment.name.search(exp_name)

            entries = self.runs.search(q)

        elif indices or indices == 0:
            if not isinstance(indices, (tuple, list)):
                indices = [indices]

            num_recs = len(self.runs)

            for idx in indices:
                if idx >= num_recs:
                    raise ValueError(
                        'Index value ({}) must be less than '
                        'number of records ({})'.format(idx, num_recs))

            entries = [self.runs.all()[ind] for ind in indices]

        else:
            raise ValueError('Must specify an experiment name, indicies or '
                             'pass custom query')

        return entries

    def _dict_to_indented_list(self, d):

        d = OrderedDict(sorted(d.items(), key=lambda t: t[0]))

        output_str = ''

        for k, v in d.items():
            output_str += '%s: %s' % (k, v)
            output_str += '\n'

        output_str = self._indent(output_str.strip(), prefix='    ')

        return output_str

    def _indent(self, message, prefix):
        """Wrapper for indenting strings in Python 2 and 3."""
        preferred_width = 150
        wrapper = textwrap.TextWrapper(initial_indent=prefix,
                                       width=preferred_width,
                                       subsequent_indent=prefix)

        lines = message.splitlines()
        formatted_lines = [wrapper.fill(lin) for lin in lines]
        formatted_text = '\n'.join(formatted_lines)

        return formatted_text
