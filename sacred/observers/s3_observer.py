import json
import os
import os.path

from sacred.commandline_options import cli_option
from sacred.dependencies import get_digest
from sacred.observers.base import RunObserver
from sacred.serializer import flatten
import re
import socket

DEFAULT_S3_PRIORITY = 20


def _is_valid_bucket(bucket_name):
    # See https://docs.aws.amazon.com/awscloudtrail/latest/userguide/
    # cloudtrail-s3-bucket-naming-requirements.html
    if len(bucket_name) < 3 or len(bucket_name) > 63:
        return False

    labels = bucket_name.split(".")
    # A bucket name consists of "labels" separated by periods
    for label in labels:
        if len(label) == 0 or label[0] == "-" or label[-1] == "-":
            # Labels must be of nonzero length,
            # and cannot begin or end with a hyphen
            return False
        for char in label:
            # Labels can only contain digits, lowercase letters, or hyphens.
            # Anything else will fail here
            if not (char.isdigit() or char.islower() or char == "-"):
                return False
    try:
        # If a name is a valid IP address, it cannot be a bucket name
        socket.inet_aton(bucket_name)
    except socket.error:
        return True


def s3_join(*args):
    return "/".join(args)


class S3Observer(RunObserver):
    VERSION = "S3Observer-0.1.0"

    def __init__(
        self,
        bucket,
        basedir,
        resource_dir=None,
        source_dir=None,
        priority=DEFAULT_S3_PRIORITY,
        region=None,
    ):
        """Constructor for a S3Observer object.

        Run when the object is first created,
        before it's used within an experiment.

        Parameters
        ----------
        bucket
            The name of the bucket you want to store results in.
            Doesn't need to contain `s3://`, but needs to be a valid bucket name
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
        region
            The AWS region in which you want to create and access
            buckets. Needs to be either set here or configured in your AWS
        """
        import boto3

        if not _is_valid_bucket(bucket):
            raise ValueError(
                "Your chosen bucket name doesn't follow AWS bucket naming rules"
            )
        resource_dir = resource_dir or "/".join([basedir, "_resources"])
        source_dir = source_dir or "/".join([basedir, "_sources"])

        self.basedir = basedir
        self.bucket = bucket
        # Keeping the convention of referring to locations in S3 as `dir`
        # because that is a useful mental model and there isn't a better word
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
        if region is not None:
            self.region = region
            self.s3 = boto3.resource("s3", region_name=region)
        else:
            session = boto3.session.Session()
            if session.region_name is not None:
                self.region = session.region_name
                self.s3 = boto3.resource("s3")
            else:
                raise ValueError(
                    "You must either pass in an AWS region name, or have a "
                    "region name specified in your AWS config file"
                )

    def _objects_exist_in_dir(self, prefix):
        # This should be run after you've confirmed the bucket
        # exists, and will error out if it does not exist

        bucket = self.s3.Bucket(self.bucket)
        all_keys = [el.key for el in bucket.objects.filter(Prefix=prefix)]
        return len(all_keys) > 0

    def _bucket_exists(self):
        from botocore.errorfactory import ClientError

        try:
            self.s3.meta.client.head_bucket(Bucket=self.bucket)
        except ClientError as er:
            if er.response["Error"]["Code"] == "404":
                return False
        return True

    def _list_s3_subdirs(self, prefix=None):
        if prefix is None:
            prefix = self.basedir
        bucket = self.s3.Bucket(self.bucket)
        all_keys = [obj.key for obj in bucket.objects.filter(Prefix=prefix)]
        subdir_match = r"{prefix}\/(.*)\/".format(prefix=prefix)
        subdirs = []
        for key in all_keys:
            match_obj = re.match(subdir_match, key)
            if match_obj is None:
                continue
            else:
                subdirs.append(match_obj.groups()[0])
        distinct_subdirs = set(subdirs)
        return list(distinct_subdirs)

    def _create_bucket(self):
        bucket_response = self.s3.create_bucket(
            Bucket=self.bucket,
            CreateBucketConfiguration={"LocationConstraint": self.region},
        )
        return bucket_response

    def _determine_run_dir(self, _id):
        if _id is None:
            bucket_exists = self._bucket_exists()
            if not bucket_exists:
                self._create_bucket()
                bucket_path_subdirs = []
            else:
                bucket_path_subdirs = self._list_s3_subdirs()

            if not bucket_path_subdirs:
                max_run_id = 0
            else:
                integer_directories = [
                    int(d) for d in bucket_path_subdirs if d.isdigit()
                ]
                if not integer_directories:
                    max_run_id = 0
                else:
                    # If there are directories under basedir that aren't
                    # numeric run directories, ignore those
                    max_run_id = max(integer_directories)

            _id = max_run_id + 1

        self.dir = s3_join(self.basedir, str(_id))
        if self._objects_exist_in_dir(self.dir):
            raise FileExistsError("S3 dir at {} already exists".format(self.dir))
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
        store_path = s3_join(store_dir, store_name)
        if len(self._list_s3_subdirs(prefix=store_path)) == 0:
            self.save_file(filename, store_path)
        return store_path, md5sum

    def put_data(self, key, binary_data):
        self.s3.Object(self.bucket, key).put(Body=binary_data)

    def save_json(self, obj, filename):
        key = s3_join(self.dir, filename)
        self.put_data(key, json.dumps(flatten(obj), sort_keys=True, indent=2))

    def save_file(self, filename, target_name=None):
        target_name = target_name or os.path.basename(filename)
        key = s3_join(self.dir, target_name)
        self.put_data(key, open(filename, "rb"))

    def save_directory(self, source_dir, target_name):
        import boto3

        # Stolen from:
        # https://github.com/boto/boto3/issues/358#issuecomment-346093506
        target_name = target_name or os.path.basename(source_dir)
        all_files = []
        for root, dirs, files in os.walk(source_dir):
            all_files += [os.path.join(root, f) for f in files]
        s3_resource = boto3.resource("s3")

        for filename in all_files:
            file_location = s3_join(
                self.dir, target_name, os.path.relpath(filename, source_dir)
            )
            s3_resource.Object(self.bucket, file_location).put(
                Body=open(filename, "rb")
            )

    def save_cout(self):
        binary_data = self.cout[self.cout_write_cursor :].encode("utf-8")
        key = s3_join(self.dir, "cout.txt")
        self.put_data(key, binary_data)
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
        if isinstance(other, S3Observer):
            return self.bucket == other.bucket and self.basedir == other.basedir
        else:
            return False


@cli_option("-S", "--s3")
def s3_option(args, run):
    """Add a S3 File observer to the experiment.

    The argument value should be `s3://<bucket>/path/to/exp`.
    """
    match_obj = re.match(r"s3:\/\/([^\/]*)\/(.*)", args)
    if match_obj is None or len(match_obj.groups()) != 2:
        raise ValueError(
            "Valid bucket specification not found. "
            "Enter bucket and directory path like: "
            "s3://<bucket>/path/to/exp"
        )
    bucket, basedir = match_obj.groups()
    run.observers.append(S3Observer(bucket=bucket, basedir=basedir))
