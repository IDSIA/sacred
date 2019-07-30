#!/usr/bin/env python
# coding=utf-8

import json
import os
import os.path

import boto3
from botocore.errorfactory import ClientError

from sacred.commandline_options import CommandLineOption
from sacred.dependencies import get_digest
from sacred.observers.base import RunObserver
from sacred.serializer import flatten
import re
import socket

DEFAULT_S3_PRIORITY = 20


def _is_valid_bucket(bucket_name):
    if len(bucket_name) < 3 or len(bucket_name) > 63:
        return False
    if '..' in bucket_name or '.-' in bucket_name or '-.' in bucket_name:
        return False
    for char in bucket_name:
        if char.isdigit():
            continue
        if char.islower():
            continue
        if char == '-':
            continue
        return False
    try:
        socket.inet_aton(bucket_name)
    except socket.error:
        # congrats, you're a valid bucket name
        return True


class S3FileObserver(RunObserver):
    ## TODO (possibly): make S3FileObserver inherit from FSO to avoid
    ## duplicating code. But this might be even messier?
    VERSION = 'S3FileObserver-0.1.0'

    @classmethod
    def create(cls, bucket, basedir, resource_dir=None, source_dir=None,
               priority=DEFAULT_S3_PRIORITY):
        resource_dir = resource_dir or os.path.join(basedir, '_resources')
        source_dir = source_dir or os.path.join(basedir, '_sources')

        return cls(bucket, basedir, resource_dir, source_dir, priority)

    def __init__(self, bucket, basedir, resource_dir, source_dir,
                 priority=DEFAULT_S3_PRIORITY):
        if not _is_valid_bucket(bucket):
            raise ValueError("Your chosen bucket name does not follow AWS "
                             "bucket naming rules")

        self.basedir = basedir
        self.bucket = bucket
        self.resource_dir = resource_dir
        self.source_dir = source_dir
        self.priority = priority
        self.dir = None
        self.run_entry = None
        self.config = None
        self.info = None
        self.cout = ""
        self.cout_write_cursor = 0
        self.s3 = boto3.resource('s3')
        self.saved_metrics = {}

    def _objects_exist_in_dir(self, prefix):
        try:
            bucket = self.s3.Bucket(self.bucket)
            all_keys = [el.key for el in bucket.objects.filter(Prefix=prefix)]
        except ClientError as er:
            if er.response['Error']['Code'] == 'NoSuchBucket':
                return None
            else:
                raise ClientError(er.response['Error']['Code'])
        return len(all_keys) > 0

    def _list_s3_subdirs(self, prefix=None):
        if prefix is None:
            prefix = self.basedir
        try:
            bucket = self.s3.Bucket(self.bucket)
            all_keys = [el.key for el in bucket.objects.filter(Prefix=prefix)]
        except ClientError as er:
            if er.response['Error']['Code'] == 'NoSuchBucket':
                return None
            else:
                raise ClientError(er.response['Error']['Code'])

        subdir_match = r'{prefix}\/(.*)\/'.format(prefix=prefix)
        subdirs = []
        for key in all_keys:
            match_obj = re.match(subdir_match, key)
            if match_obj is None:
                import pdb; pdb.set_trace()
                continue
            else:
                subdirs.append(match_obj.groups()[0])
        distinct_subdirs = set(subdirs)
        return list(distinct_subdirs)

    def _create_bucket(self):
        session = boto3.session.Session()
        current_region = session.region_name or 'us-west-2'
        bucket_response = self.s3.create_bucket(
            Bucket=self.bucket,
            CreateBucketConfiguration={
                'LocationConstraint': current_region})
        return bucket_response

    def _determine_run_dir(self, _id):
        if _id is None:
            bucket_path_subdirs = self._list_s3_subdirs()
            if bucket_path_subdirs is None:
                self._create_bucket()

            if bucket_path_subdirs is None or len(bucket_path_subdirs) == 0:
                max_run_id = 0
            else:
                integer_directories = [int(d) for d in bucket_path_subdirs
                                  if d.isdigit()]
                if len(integer_directories) == 0:
                    max_run_id = 0
                else:
                    max_run_id = max(integer_directories)

            _id = max_run_id + 1

        self.dir = os.path.join(self.basedir, str(_id))
        if self._objects_exist_in_dir(self.dir):
            raise FileExistsError(f"S3 dir at {self.dir} already exists")
        return _id

    def queued_event(self, ex_info, command, host_info, queue_time, config,
                     meta_info, _id):
        _id = self._determine_run_dir(_id)

        self.run_entry = {
            'experiment': dict(ex_info),
            'command': command,
            'host': dict(host_info),
            'meta': meta_info,
            'status': 'QUEUED',
        }
        self.config = config
        self.info = {}

        self.save_json(self.run_entry, 'run.json')
        self.save_json(self.config, 'config.json')

        for s, m in ex_info['sources']:
            self.save_file(s)

        return _id

    def save_sources(self, ex_info):
        base_dir = ex_info['base_dir']
        source_info = []
        for s, m in ex_info['sources']:
            abspath = os.path.join(base_dir, s)
            store_path, md5sum = self.find_or_save(abspath, self.source_dir)
            source_info.append([s, os.path.relpath(store_path, self.basedir)])
        return source_info

    def started_event(self, ex_info, command, host_info, start_time, config,
                      meta_info, _id):

        _id = self._determine_run_dir(_id)

        ex_info['sources'] = self.save_sources(ex_info)

        self.run_entry = {
            'experiment': dict(ex_info),
            'command': command,
            'host': dict(host_info),
            'start_time': start_time.isoformat(),
            'meta': meta_info,
            'status': 'RUNNING',
            'resources': [],
            'artifacts': [],
            'heartbeat': None
        }
        self.config = config
        self.info = {}
        self.cout = ""
        self.cout_write_cursor = 0

        self.save_json(self.run_entry, 'run.json')
        self.save_json(self.config, 'config.json')
        self.save_cout()

        return _id

    def find_or_save(self, filename, store_dir):
        source_name, ext = os.path.splitext(os.path.basename(filename))
        md5sum = get_digest(filename)
        store_name = source_name + '_' + md5sum + ext
        store_path = os.path.join(store_dir, store_name)
        if len(self._list_s3_subdirs(prefix=store_path)) == 0:
            self.save_file(filename, store_path)
        return store_path, md5sum

    def put_data(self, key, binary_data):
        self.s3.Object(self.bucket, key).put(Body=binary_data)

    def save_json(self, obj, filename):
        key = os.path.join(self.dir, filename)
        self.put_data(key, json.dumps(flatten(obj),
                                      sort_keys=True, indent=2))

    def save_file(self, filename, target_name=None):
        target_name = target_name or os.path.basename(filename)
        key = os.path.join(self.dir, target_name)
        self.put_data(key, open(filename, 'rb'))

    def save_directory(self, source_dir, target_name):
        # Stolen from:
        # https://github.com/boto/boto3/issues/358#issuecomment-346093506
        target_name = target_name or os.path.basename(source_dir)
        all_files = []
        for root, dirs, files in os.walk(source_dir):
            all_files += [os.path.join(root, f) for f in files]
        s3_resource = boto3.resource('s3')

        for filename in all_files:
            file_location = os.path.join(self.dir, target_name,
                                         os.path.relpath(filename, source_dir))
            s3_resource.Object(self.bucket,
                               file_location).put(Body=open(filename, 'rb'))

    def save_cout(self):
        binary_data = self.cout[self.cout_write_cursor:].encode("utf-8")
        key = os.path.join(self.dir, 'cout.txt')
        self.put_data(key, binary_data)
        self.cout_write_cursor = len(self.cout)


    ## same as FSO
    def heartbeat_event(self, info, captured_out, beat_time, result):
        self.info = info
        self.run_entry['heartbeat'] = beat_time.isoformat()
        self.run_entry['result'] = result
        self.cout = captured_out
        self.save_cout()
        self.save_json(self.run_entry, 'run.json')
        if self.info:
            self.save_json(self.info, 'info.json')

    def completed_event(self, stop_time, result):
        self.run_entry['stop_time'] = stop_time.isoformat()
        self.run_entry['result'] = result
        self.run_entry['status'] = 'COMPLETED'

        self.save_json(self.run_entry, 'run.json')

    def interrupted_event(self, interrupt_time, status):
        self.run_entry['stop_time'] = interrupt_time.isoformat()
        self.run_entry['status'] = status
        self.save_json(self.run_entry, 'run.json')

    def failed_event(self, fail_time, fail_trace):
        self.run_entry['stop_time'] = fail_time.isoformat()
        self.run_entry['status'] = 'FAILED'
        self.run_entry['fail_trace'] = fail_trace
        self.save_json(self.run_entry, 'run.json')

    def resource_event(self, filename):
        store_path, md5sum = self.find_or_save(filename, self.resource_dir)
        self.run_entry['resources'].append([filename, store_path])
        self.save_json(self.run_entry, 'run.json')

    def artifact_event(self, name, filename, metadata=None, content_type=None):
        self.save_file(filename, name)
        self.run_entry['artifacts'].append(name)
        self.save_json(self.run_entry, 'run.json')

    def artifact_directory_event(self, name, filename):
        self.save_directory(filename, name)
        self.run_entry['artifacts'].append(name + "/")
        self.save_json(self.run_entry, 'run.json')

    def log_metrics(self, metrics_by_name, info):
        """Store new measurements into metrics.json.
        """

        for metric_name, metric_ptr in metrics_by_name.items():

            if metric_name not in self.saved_metrics:
                self.saved_metrics[metric_name] = {"values": [],
                                                   "steps": [],
                                                   "timestamps": []}

            self.saved_metrics[metric_name]["values"] += metric_ptr["values"]
            self.saved_metrics[metric_name]["steps"] += metric_ptr["steps"]

            timestamps_norm = [ts.isoformat()
                               for ts in metric_ptr["timestamps"]]
            self.saved_metrics[metric_name]["timestamps"] += timestamps_norm

        self.save_json(self.saved_metrics, 'metrics.json')

    def __eq__(self, other):
        if isinstance(other, S3FileObserver):
            return (self.bucket == other.bucket
                    and self.basedir == other.basedir)
        return False


class S3StorageOption(CommandLineOption):
    """Add a S3 File observer to the experiment."""

    short_flag = 'S3'
    arg = 'BUCKET_PATH'
    arg_description = "s3://<bucket>/path/to/exp"

    @classmethod
    def apply(cls, args, run):
        match_obj = re.match(r's3:\/\/([^\/]*)\/(.*)', args)
        if match_obj is None or len(match_obj.groups()) != 2:
            raise ValueError("Valid bucket specification not found. "
                             "Enter bucket and directory path like: "
                             "s3://<bucket>/path/to/exp")
        bucket, basedir = match_obj.groups()
        run.observers.append(S3FileObserver.create(bucket=bucket,
                                                   basedir=basedir))
