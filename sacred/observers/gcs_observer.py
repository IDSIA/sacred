import json
import os
import os.path
import re
from typing import Optional

from sacred.commandline_options import cli_option
from sacred.dependencies import get_digest
from sacred.observers.base import RunObserver
from sacred.serializer import flatten
from sacred.utils import PathType

DEFAULT_GCS_PRIORITY = 20


def _is_valid_bucket(bucket_name: str):
    """Validates correctness of bucket naming.

    Reference: https://cloud.google.com/storage/docs/naming
    """
    if bucket_name.startswith("gs://"):
        return False

    if len(bucket_name) < 3 or len(bucket_name) > 63:
        return False

    # IP address
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", bucket_name):
        return False

    if not re.fullmatch(r"([^A-Z]|-|_|[.]|)+", bucket_name):
        return False

    if ".." in bucket_name:
        return False

    if "goog" in bucket_name or "g00g" in bucket_name:
        return False

    return True


def gcs_join(*args):
    return "/".join(args)


class GoogleCloudStorageObserver(RunObserver):
    VERSION = "GoogleCloudStorageObserver-0.1.0"

    def __init__(
        self,
        bucket: str,
        basedir: PathType,
        resource_dir: Optional[PathType] = None,
        source_dir: Optional[PathType] = None,
        priority: Optional[int] = DEFAULT_GCS_PRIORITY,
    ):
        """Constructor for a GoogleCloudStorageObserver object.

        Run when the object is first created,
        before it's used within an experiment.

        Parameters
        ----------
        bucket
            The name of the bucket you want to store results in.
            Needs to be a valid bucket name without 'gs://'
        basedir
            The relative path inside your bucket where you want this experiment to store results
        resource_dir
            Where to store resources for this experiment. By
            default, will be <basedir>/_resources
        source_dir
            Where to store code sources for this experiment. By
            default, will be <basedir>/sources
        priority
            The priority to assign to this observer if
            multiple observers are present
        """
        if not _is_valid_bucket(bucket):
            raise ValueError(
                "Your chosen bucket name doesn't follow Google Cloud Storage bucket naming rules"
            )
        resource_dir = resource_dir or "/".join([basedir, "_resources"])
        source_dir = source_dir or "/".join([basedir, "_sources"])

        self.basedir = basedir
        self.bucket_id = bucket

        self.resource_dir = resource_dir
        self.source_dir = source_dir
        self.priority = priority
        self.dir = None
        self.run_entry = None
        self.config = None
        self.info = None
        self.cout = ""
        self.cout_write_cursor = 0
        self.saved_metrics = {}

        from google.cloud import storage
        import google.auth.exceptions

        try:
            client = storage.Client()
        except google.auth.exceptions.DefaultCredentialsError as e:
            raise ConnectionError(
                "Could not create Google Cloud Storage observer, are you "
                "sure that you have set environment variable GOOGLE_APPLICATION_CREDENTIALS?"
            ) from e

        self.bucket = client.bucket(bucket)

    def _objects_exist_in_dir(self, prefix):
        # This should be run after you've confirmed the bucket
        # exists, and will error out if it does not exist
        all_blobs = [blob for blob in self.bucket.list_blobs(prefix=prefix)]
        return len(all_blobs) > 0

    def _list_gcs_subdirs(self, prefix=None):
        if prefix is None:
            prefix = self.basedir

        iterator = self.bucket.list_blobs(prefix=prefix, delimiter="/")
        prefixes = set()
        for page in iterator.pages:
            prefixes.update(page.prefixes)

        return list(prefixes)

    def _determine_run_dir(self, _id):
        if _id is None:
            basepath = os.path.join(self.basedir, "")
            bucket_path_subdirs = self._list_gcs_subdirs(prefix=basepath)

            if not bucket_path_subdirs:
                max_run_id = 0
            else:
                relative_paths = [
                    path.replace(self.basedir, "").strip("/")
                    for path in bucket_path_subdirs
                ]
                integer_directories = [int(d) for d in relative_paths if d.isdigit()]
                if not integer_directories:
                    max_run_id = 0
                else:
                    # If there are directories under basedir that aren't
                    # numeric run directories, ignore those
                    max_run_id = max(integer_directories)

            _id = max_run_id + 1

        self.dir = gcs_join(self.basedir, str(_id))
        if self._objects_exist_in_dir(self.dir):
            raise FileExistsError("GCS dir at {} already exists".format(self.dir))
        return _id

    def queued_event(
        self, ex_info, command, host_info, queue_time, config, meta_info, _id
    ):
        _id = self._determine_run_dir(_id)

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

        for s, m in ex_info["sources"]:
            self.save_file(s)

        return _id

    def save_sources(self, ex_info):
        base_dir = ex_info["base_dir"]
        source_info = []
        for s, m in ex_info["sources"]:
            abspath = os.path.join(base_dir, s)
            store_path, md5sum = self.find_or_save(abspath, self.source_dir)
            source_info.append([s, os.path.relpath(store_path, self.basedir)])
        return source_info

    def started_event(
        self, ex_info, command, host_info, start_time, config, meta_info, _id
    ):

        _id = self._determine_run_dir(_id)

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

        return _id

    def find_or_save(self, filename, store_dir):
        source_name, ext = os.path.splitext(os.path.basename(filename))
        md5sum = get_digest(filename)
        store_name = source_name + "_" + md5sum + ext
        store_path = gcs_join(store_dir, store_name)
        if len(self._list_gcs_subdirs(prefix=store_path)) == 0:
            self.save_file_to_base(filename, store_path)
        return store_path, md5sum

    def put_data(self, key, binary_data):
        blob = self.bucket.blob(key)
        blob.upload_from_file(binary_data)

    def save_json(self, obj, filename):
        key = gcs_join(self.dir, filename)
        blob = self.bucket.blob(key)
        blob.upload_from_string(
            json.dumps(flatten(obj), sort_keys=True, indent=2), content_type="text/json"
        )

    def save_file(self, filename, target_name=None):
        target_name = target_name or os.path.basename(filename)
        key = gcs_join(self.dir, target_name)
        self.put_data(key, open(filename, "rb"))

    def save_file_to_base(self, filename, target_name=None):
        target_name = target_name or os.path.basename(filename)
        self.put_data(target_name, open(filename, "rb"))

    def save_directory(self, source_dir, target_name):
        target_name = target_name or os.path.basename(source_dir)
        all_files = []
        for root, dirs, files in os.walk(source_dir):
            all_files += [os.path.join(root, f) for f in files]

        for filename in all_files:
            file_location = gcs_join(
                self.dir, target_name, os.path.relpath(filename, source_dir)
            )
            self.put_data(file_location, open(filename, "rb"))

    def save_cout(self):
        binary_data = self.cout[self.cout_write_cursor :].encode("utf-8")
        key = gcs_join(self.dir, "cout.txt")
        blob = self.bucket.blob(key)
        blob.upload_from_string(binary_data, content_type="text/plain")
        self.cout_write_cursor = len(self.cout)

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

    def interrupted_event(self, interrupt_time, status):
        self.run_entry["stop_time"] = interrupt_time.isoformat()
        self.run_entry["status"] = status
        self.save_json(self.run_entry, "run.json")

    def failed_event(self, fail_time, fail_trace):
        self.run_entry["stop_time"] = fail_time.isoformat()
        self.run_entry["status"] = "FAILED"
        self.run_entry["fail_trace"] = fail_trace
        self.save_json(self.run_entry, "run.json")

    def resource_event(self, filename):
        store_path, md5sum = self.find_or_save(filename, self.resource_dir)
        self.run_entry["resources"].append([filename, store_path])
        self.save_json(self.run_entry, "run.json")

    def artifact_event(self, name, filename, metadata=None, content_type=None):
        self.save_file(filename, name)
        self.run_entry["artifacts"].append(name)
        self.save_json(self.run_entry, "run.json")

    def log_metrics(self, metrics_by_name, info):
        """Store new measurements into metrics.json."""
        for metric_name, metric_ptr in metrics_by_name.items():

            if metric_name not in self.saved_metrics:
                self.saved_metrics[metric_name] = {
                    "values": [],
                    "steps": [],
                    "timestamps": [],
                }

            self.saved_metrics[metric_name]["values"] += metric_ptr["values"]
            self.saved_metrics[metric_name]["steps"] += metric_ptr["steps"]

            timestamps_norm = [ts.isoformat() for ts in metric_ptr["timestamps"]]
            self.saved_metrics[metric_name]["timestamps"] += timestamps_norm

        self.save_json(self.saved_metrics, "metrics.json")

    def __eq__(self, other):
        if isinstance(other, GoogleCloudStorageObserver):
            return self.bucket_id == other.bucket_id and self.basedir == other.basedir
        else:
            return False


@cli_option("-G", "--gcs")
def gcs_option(args, run):
    """Add a Google Cloud Storage File observer to the experiment.

    The argument value should be `gs://<bucket>/path/to/exp`.
    """
    match_obj = re.match(r"gs:\/\/([^\/]*)\/(.*)", args)
    if match_obj is None or len(match_obj.groups()) != 2:
        raise ValueError(
            "Valid bucket specification not found. "
            "Enter bucket and directory path like: "
            "gs://<bucket>/path/to/exp"
        )
    bucket, basedir = match_obj.groups()
    run.observers.append(GoogleCloudStorageObserver(bucket=bucket, basedir=basedir))
