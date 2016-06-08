#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import os
import os.path
import tempfile
import json
from datetime import datetime

from sacred.commandline_options import CommandLineOption
from sacred.dependencies import get_digest
from sacred.observers.base import RunObserver


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError ("Type not serializable")


class FlatfileObserver(RunObserver):

    def __init__(self, basedir):
        if not os.path.exists(basedir):
            os.makedirs(basedir)
        self.basedir = basedir
        self.run_entry = None

    def started_event(self, ex_info, command, host_info, start_time, config,
                      meta_info, _id):
        if _id is None:
            self.dir = tempfile.mkdtemp(prefix='run_', dir=self.basedir)
        else:
            self.dir = os.path.join(self.basedir, str(_id))
            os.mkdir(self.dir)

        self.run_entry = {
            'experiment': dict(ex_info),
            'command': command,
            'host': dict(host_info),
            'start_time': start_time,
            'config': config,
            'meta': meta_info,
            'status': 'RUNNING',
            'resources': [],
            'artifacts': [],
            'info': {},
            'heartbeat': None
        }
        self.save()
        self.save_cout('')

        for s, m in ex_info['sources']:
            self.save_file(s)

        return os.path.relpath(self.dir, self.basedir) if _id is None else _id

    def save(self):
        with open(os.path.join(self.dir, 'run.json'), 'w') as f:
            json.dump(self.run_entry, f, indent=2, sort_keys=True,
                      default=json_serial)

    def save_file(self, filename):
        from shutil import copyfile
        fn = os.path.basename(filename)
        copyfile(filename, os.path.join(self.dir, fn))

    def save_cout(self, cout):
        with open(os.path.join(self.dir, 'cout.txt'), 'w') as f:
            f.write(cout)

    def heartbeat_event(self, info, captured_out, beat_time):
        self.run_entry['info'] = info
        self.save_cout(captured_out)
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
        self.save_file(filename)
        md5hash = get_digest(filename)
        self.run_entry['resources'].append((filename, md5hash))
        self.save()

    def artifact_event(self, filename):
        self.save_file(filename)
        self.run_entry['artifacts'].append(filename)
        self.save()


class FlatfileOption(CommandLineOption):
    """Add a flat-file observer to the experiment."""

    short_flag = 'F'
    arg = 'BASEDIR'
    arg_description = "Base-directory to write the runs to"

    @classmethod
    def apply(cls, args, run):
        run.observers.append(FlatfileObserver(args))

