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
from sacred import optional as opt


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")


class FlatfileObserver(RunObserver):

    def __init__(self, basedir):
        if not os.path.exists(basedir):
            os.makedirs(basedir)
        self.basedir = basedir
        self.run_entry = None
        self.config = None
        self.info = None
        self.cout = ""

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
            'meta': meta_info,
            'status': 'RUNNING',
            'resources': [],
            'artifacts': [],
            'heartbeat': None
        }
        self.config = config
        self.info = {}
        self.cout = ""

        self.save_json(self.run_entry, 'run.json')
        self.save_json(self.config, 'config.json')
        self.save_cout()

        for s, m in ex_info['sources']:
            self.save_file(s)

        return os.path.relpath(self.dir, self.basedir) if _id is None else _id

    def save_json(self, obj, filename):
        with open(os.path.join(self.dir, filename), 'w') as f:
            json.dump(obj, f, indent=2, sort_keys=True,
                      default=json_serial)

    def save_file(self, filename):
        from shutil import copyfile
        fn = os.path.basename(filename)
        copyfile(filename, os.path.join(self.dir, fn))

    def save_cout(self):
        with open(os.path.join(self.dir, 'cout.txt'), 'w') as f:
            f.write(self.cout)

    def render_template(self):
        print('RENDERING TEMPLATE')
        template_name = os.path.join(self.basedir, 'template.html')
        print(template_name)
        if opt.has_mako and os.path.exists(template_name):
            print('ACTUALLY DOING IT!')
            from mako.template import Template
            template = Template(filename=template_name)
            report = template.render(run=self.run_entry,
                                     config=self.config,
                                     info=self.info,
                                     cout=self.cout)
            print('Rendered it!')
            with open(os.path.join(self.dir, 'report.html'), 'w') as f:
                f.write(report)

    def heartbeat_event(self, info, captured_out, beat_time):
        self.cout = captured_out
        self.info = info
        self.run_entry['heartbeat'] = beat_time

        self.save_cout()
        self.save_json(self.run_entry, 'run.json')
        self.save_json(self.info, 'info.json')

    def completed_event(self, stop_time, result):
        self.run_entry['stop_time'] = stop_time
        self.run_entry['result'] = result
        self.run_entry['status'] = 'COMPLETED'

        self.save_json(self.run_entry, 'run.json')
        self.render_template()

    def interrupted_event(self, interrupt_time, status):
        self.run_entry['stop_time'] = interrupt_time
        self.run_entry['status'] = status
        self.save_json(self.run_entry, 'run.json')
        self.render_template()

    def failed_event(self, fail_time, fail_trace):
        self.run_entry['stop_time'] = fail_time
        self.run_entry['status'] = 'FAILED'
        self.run_entry['fail_trace'] = fail_trace
        self.save_json(self.run_entry, 'run.json')
        self.render_template()

    def resource_event(self, filename):
        self.save_file(filename)
        md5hash = get_digest(filename)
        self.run_entry['resources'].append((filename, md5hash))
        self.save_json(self.run_entry, 'run.json')

    def artifact_event(self, filename):
        self.save_file(filename)
        self.run_entry['artifacts'].append(filename)
        self.save_json(self.run_entry, 'run.json')


class FlatfileOption(CommandLineOption):
    """Add a flat-file observer to the experiment."""

    short_flag = 'F'
    arg = 'BASEDIR'
    arg_description = "Base-directory to write the runs to"

    @classmethod
    def apply(cls, args, run):
        run.observers.append(FlatfileObserver(args))

