#!/usr/bin/env python
# coding=utf-8

import json
import os
import os.path
from pathlib import Path
from typing import Optional
import warnings

from shutil import copyfile, SameFileError

from sacred.commandline_options import cli_option
from sacred.dependencies import get_digest
from sacred.observers.base import RunObserver
from sacred import optional as opt
from sacred.serializer import flatten
from sacred.utils import PathType


DEFAULT_FILE_STORAGE_PRIORITY = 20


class FileStorageObserver(RunObserver):
    VERSION = "FileStorageObserver-0.7.0"

    @classmethod
    def create(cls, *args, **kwargs):
        warnings.warn(
            "FileStorageObserver.create(...) is deprecated. "
            "Please use FileStorageObserver(...) instead.",
            DeprecationWarning,
        )
        return cls(*args, **kwargs)

    def __init__(
        self,
        basedir: PathType,
        resource_dir: Optional[PathType] = None,
        source_dir: Optional[PathType] = None,
        template: Optional[PathType] = None,
        priority: int = DEFAULT_FILE_STORAGE_PRIORITY,
        copy_artifacts: bool = True,
        copy_sources: bool = True,
    ):
        basedir = Path(basedir)
        resource_dir = resource_dir or basedir / "_resources"
        source_dir = source_dir or basedir / "_sources"
        if template is not None:
            if not os.path.exists(template):
                raise FileNotFoundError(
                    "Couldn't find template file '{}'".format(template)
                )
        else:
            template = basedir / "template.html"
            if not template.exists():
                template = None
        self.initialize(
            basedir,
            resource_dir,
            source_dir,
            template,
            priority,
            copy_artifacts,
            copy_sources,
        )

    def initialize(
        self,
        basedir,
        resource_dir,
        source_dir,
        template,
        priority=DEFAULT_FILE_STORAGE_PRIORITY,
        copy_artifacts=True,
        copy_sources=True,
    ):
        self.basedir = str(basedir)
        self.resource_dir = resource_dir
        self.source_dir = source_dir
        self.template = template
        self.priority = priority
        self.copy_artifacts = copy_artifacts
        self.copy_sources = copy_sources
        self.dir = None
        self.run_entry = None
        self.config = None
        self.info = None
        self.cout = ""
        self.cout_write_cursor = 0

    @classmethod
    def create_from(cls, *args, **kwargs):
        self = cls.__new__(cls)  # skip __init__ call
        self.initialize(*args, **kwargs)
        return self

    def _maximum_existing_run_id(self):
        dir_nrs = [
            int(d)
            for d in os.listdir(self.basedir)
            if os.path.isdir(os.path.join(self.basedir, d)) and d.isdigit()
        ]
        if dir_nrs:
            return max(dir_nrs)
        else:
            return 0

    def _make_dir(self, _id):
        new_dir = os.path.join(self.basedir, str(_id))
        os.mkdir(new_dir)
        self.dir = new_dir  # set only if mkdir is successful

    def _make_run_dir(self, _id):
        os.makedirs(self.basedir, exist_ok=True)
        self.dir = None
        if _id is None:
            fail_count = 0
            _id = self._maximum_existing_run_id() + 1
            while self.dir is None:
                try:
                    self._make_dir(_id)
                except FileExistsError:  # Catch race conditions
                    if fail_count < 1000:
                        fail_count += 1
                        _id += 1
                    else:  # expect that something else went wrong
                        raise
        else:
            self.dir = os.path.join(self.basedir, str(_id))
            os.mkdir(self.dir)

    def queued_event(
        self, ex_info, command, host_info, queue_time, config, meta_info, _id
    ):
        self._make_run_dir(_id)

        self.run_entry = {
            "experiment": dict(ex_info),
            "command": command,
            "host": dict(host_info),
            "meta": meta_info,
            "status": "QUEUED",
        }
        self.config = config
        self.info = {}

        self.save_json(self.run_entry, "run.json")
        self.save_json(self.config, "config.json")

        if self.copy_sources:
            for s, _ in ex_info["sources"]:
                self.save_file(s)

        return os.path.relpath(self.dir, self.basedir) if _id is None else _id

    def save_sources(self, ex_info):
        base_dir = ex_info["base_dir"]
        source_info = []
        for s, _ in ex_info["sources"]:
            abspath = os.path.join(base_dir, s)
            if self.copy_sources:
                store_path = self.find_or_save(abspath, self.source_dir)
            else:
                store_path = abspath
            relative_source = os.path.relpath(str(store_path), self.basedir)
            source_info.append([s, relative_source])
        return source_info

    def started_event(
        self, ex_info, command, host_info, start_time, config, meta_info, _id
    ):
        self._make_run_dir(_id)

        ex_info["sources"] = self.save_sources(ex_info)

        self.run_entry = {
            "experiment": dict(ex_info),
            "command": command,
            "host": dict(host_info),
            "start_time": start_time.isoformat(),
            "meta": meta_info,
            "status": "RUNNING",
            "resources": [],
            "artifacts": [],
            "heartbeat": None,
        }
        self.config = config
        self.info = {}
        self.cout = ""
        self.cout_write_cursor = 0

        self.save_json(self.run_entry, "run.json")
        self.save_json(self.config, "config.json")
        self.save_cout()

        return os.path.relpath(self.dir, self.basedir) if _id is None else _id

    def find_or_save(self, filename, store_dir: Path):
        try:
            Path(filename).resolve().relative_to(Path(self.basedir).resolve())
            is_relative_to = True
        except ValueError:
            is_relative_to = False

        if is_relative_to and not self.copy_artifacts:
            return filename
        else:
            store_dir.mkdir(parents=True, exist_ok=True)
            source_name, ext = os.path.splitext(os.path.basename(filename))
            md5sum = get_digest(filename)
            store_name = source_name + "_" + md5sum + ext
            store_path = store_dir / store_name
            if not store_path.exists():
                copyfile(filename, str(store_path))
            return store_path

    def save_json(self, obj, filename):
        with open(os.path.join(self.dir, filename), "w") as f:
            json.dump(flatten(obj), f, sort_keys=True, indent=2)
            f.flush()

    def save_file(self, filename, target_name=None):
        target_name = target_name or os.path.basename(filename)
        blacklist = ["run.json", "config.json", "cout.txt", "metrics.json"]
        blacklist = [os.path.join(self.dir, x) for x in blacklist]
        dest_file = os.path.join(self.dir, target_name)
        if dest_file in blacklist:
            raise FileExistsError(
                "You are trying to overwrite a file necessary for the "
                "FileStorageObserver. "
                "The list of blacklisted files is: {}".format(blacklist)
            )
        try:
            copyfile(filename, dest_file)
        except SameFileError:
            pass

    def save_cout(self):
        with open(os.path.join(self.dir, "cout.txt"), "ab") as f:
            f.write(self.cout[self.cout_write_cursor :].encode("utf-8"))
            self.cout_write_cursor = len(self.cout)

    def render_template(self):
        if opt.has_mako and self.template:
            from mako.template import Template

            template = Template(filename=self.template)
            report = template.render(
                run=self.run_entry,
                config=self.config,
                info=self.info,
                cout=self.cout,
                savedir=self.dir,
            )
            ext = self.template.suffix
            with open(os.path.join(self.dir, "report" + ext), "w") as f:
                f.write(report)

    def heartbeat_event(self, info, captured_out, beat_time, result):
        self.info = info
        self.run_entry["heartbeat"] = beat_time.isoformat()
        self.run_entry["result"] = result
        self.cout = captured_out
        self.save_cout()
        self.save_json(self.run_entry, "run.json")
        if self.info:
            self.save_json(self.info, "info.json")

    def completed_event(self, stop_time, result):
        self.run_entry["stop_time"] = stop_time.isoformat()
        self.run_entry["result"] = result
        self.run_entry["status"] = "COMPLETED"

        self.save_json(self.run_entry, "run.json")
        self.render_template()

    def interrupted_event(self, interrupt_time, status):
        self.run_entry["stop_time"] = interrupt_time.isoformat()
        self.run_entry["status"] = status
        self.save_json(self.run_entry, "run.json")
        self.render_template()

    def failed_event(self, fail_time, fail_trace):
        self.run_entry["stop_time"] = fail_time.isoformat()
        self.run_entry["status"] = "FAILED"
        self.run_entry["fail_trace"] = fail_trace
        self.save_json(self.run_entry, "run.json")
        self.render_template()

    def resource_event(self, filename):
        store_path = self.find_or_save(filename, self.resource_dir)
        self.run_entry["resources"].append([filename, str(store_path)])
        self.save_json(self.run_entry, "run.json")

    def artifact_event(self, name, filename, metadata=None, content_type=None):
        self.save_file(filename, name)
        self.run_entry["artifacts"].append(name)
        self.save_json(self.run_entry, "run.json")

    def log_metrics(self, metrics_by_name, info):
        """Store new measurements into metrics.json."""
        try:
            metrics_path = os.path.join(self.dir, "metrics.json")
            with open(metrics_path, "r") as f:
                saved_metrics = json.load(f)
        except IOError:
            # We haven't recorded anything yet. Start Collecting.
            saved_metrics = {}

        for metric_name, metric_ptr in metrics_by_name.items():

            if metric_name not in saved_metrics:
                saved_metrics[metric_name] = {
                    "values": [],
                    "steps": [],
                    "timestamps": [],
                }

            saved_metrics[metric_name]["values"] += metric_ptr["values"]
            saved_metrics[metric_name]["steps"] += metric_ptr["steps"]

            # Manually convert them to avoid passing a datetime dtype handler
            # when we're trying to convert into json.
            timestamps_norm = [ts.isoformat() for ts in metric_ptr["timestamps"]]
            saved_metrics[metric_name]["timestamps"] += timestamps_norm

        self.save_json(saved_metrics, "metrics.json")

    def __eq__(self, other):
        if isinstance(other, FileStorageObserver):
            return self.basedir == other.basedir
        return False


@cli_option("-F", "--file_storage")
def file_storage_option(args, run):
    """Add a file-storage observer to the experiment.

    The value of the arguement should be the
    base-directory to write the runs to
    """
    run.observers.append(FileStorageObserver(args))
