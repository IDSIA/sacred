from typing import Optional, Union
import mimetypes
import os.path
import pickle
import re
import sys
import time
from tempfile import NamedTemporaryFile
import warnings

import sacred.optional as opt
from sacred.commandline_options import cli_option
from sacred.dependencies import get_digest
from sacred.observers.base import RunObserver
from sacred.observers.queue import QueueObserver
from sacred.serializer import flatten
from sacred.utils import ObserverError, PathType
import pkg_resources

DEFAULT_MONGO_PRIORITY = 30

# This ensures consistent mimetype detection across platforms.
mimetype_detector = mimetypes.MimeTypes(
    filenames=[pkg_resources.resource_filename("sacred", "data/mime.types")]
)


def force_valid_bson_key(key):
    key = str(key)
    if key.startswith("$"):
        key = "@" + key[1:]
    key = key.replace(".", ",")
    return key


def force_bson_encodeable(obj):
    import bson

    if isinstance(obj, dict):
        try:
            bson.BSON.encode(obj, check_keys=True)
            return obj
        except bson.InvalidDocument:
            return {
                force_valid_bson_key(k): force_bson_encodeable(v)
                for k, v in obj.items()
            }

    elif opt.has_numpy and isinstance(obj, opt.np.ndarray):
        return obj
    else:
        try:
            bson.BSON.encode({"dict_just_for_testing": obj})
            return obj
        except bson.InvalidDocument:
            return str(obj)


class MongoObserver(RunObserver):
    COLLECTION_NAME_BLACKLIST = {
        "fs.files",
        "fs.chunks",
        "_properties",
        "system.indexes",
        "search_space",
        "search_spaces",
    }
    VERSION = "MongoObserver-0.7.0"

    @classmethod
    def create(cls, *args, **kwargs):
        warnings.warn(
            "MongoObserver.create(...) is deprecated. "
            "Please use MongoObserver(...) instead.",
            DeprecationWarning,
        )
        return cls(*args, **kwargs)

    def __init__(
        self,
        url: Optional[str] = None,
        db_name: str = "sacred",
        collection: str = "runs",
        collection_prefix: str = "",
        overwrite: Optional[Union[int, str]] = None,
        priority: int = DEFAULT_MONGO_PRIORITY,
        client: Optional["pymongo.MongoClient"] = None,
        failure_dir: Optional[PathType] = None,
        **kwargs,
    ):
        """Initializer for MongoObserver.

        Parameters
        ----------
        url
            Mongo URI to connect to.
        db_name
            Database to connect to.
        collection
            Collection to write the runs to. (default: "runs").
            **DEPRECATED**, please use collection_prefix instead.
        collection_prefix
            Prefix the runs and metrics collection,
            i.e. runs will be stored to PREFIX_runs, metrics to PREFIX_metrics.
            If empty runs are stored to 'runs', metrics to 'metrics'.
        overwrite
            _id of a run that should be overwritten.
        priority
            (default 30)
        client
            Client to connect to. Do not use client and URL together.
        failure_dir
            Directory to save the run of a failed observer to.
        """
        import pymongo
        import gridfs

        if client is not None:
            if not isinstance(client, pymongo.MongoClient):
                raise ValueError(
                    "client needs to be a pymongo.MongoClient, "
                    "but is {} instead".format(type(client))
                )
            if url is not None:
                raise ValueError("Cannot pass both a client and a url.")
        else:
            client = pymongo.MongoClient(url, **kwargs)

        self._client = client
        database = client[db_name]
        if collection != "runs":
            # the 'old' way of setting a custom collection name
            # still works as before for backward compatibility
            warnings.warn(
                'Argument "collection" is deprecated. '
                'Please use "collection_prefix" instead.',
                DeprecationWarning,
            )
            if collection_prefix != "":
                raise ValueError("Cannot pass both collection and a collection prefix.")
            runs_collection_name = collection
            metrics_collection_name = "metrics"
        else:
            if collection_prefix != "":
                # separate prefix from 'runs' / 'collections' by an underscore.
                collection_prefix = "{}_".format(collection_prefix)

            runs_collection_name = "{}runs".format(collection_prefix)
            metrics_collection_name = "{}metrics".format(collection_prefix)

        if runs_collection_name in MongoObserver.COLLECTION_NAME_BLACKLIST:
            raise KeyError(
                'Collection name "{}" is reserved. '
                "Please use a different one.".format(runs_collection_name)
            )

        if metrics_collection_name in MongoObserver.COLLECTION_NAME_BLACKLIST:
            raise KeyError(
                'Collection name "{}" is reserved. '
                "Please use a different one.".format(metrics_collection_name)
            )

        runs_collection = database[runs_collection_name]
        metrics_collection = database[metrics_collection_name]
        fs = gridfs.GridFS(database)
        self.initialize(
            runs_collection,
            fs,
            overwrite=overwrite,
            metrics_collection=metrics_collection,
            failure_dir=failure_dir,
            priority=priority,
        )

    def initialize(
        self,
        runs_collection,
        fs,
        overwrite=None,
        metrics_collection=None,
        failure_dir=None,
        priority=DEFAULT_MONGO_PRIORITY,
    ):
        self.runs = runs_collection
        self.metrics = metrics_collection
        self.fs = fs
        if overwrite is not None:
            overwrite = int(overwrite)
            run = self.runs.find_one({"_id": overwrite})
            if run is None:
                raise RuntimeError(
                    "Couldn't find run to overwrite with " "_id='{}'".format(overwrite)
                )
            else:
                overwrite = run
        self.overwrite = overwrite
        self.run_entry = None
        self.priority = priority
        self.failure_dir = failure_dir

    @classmethod
    def create_from(cls, *args, **kwargs):
        self = cls.__new__(cls)  # skip __init__ call
        self.initialize(*args, **kwargs)
        return self

    def queued_event(
        self, ex_info, command, host_info, queue_time, config, meta_info, _id
    ):
        if self.overwrite is not None:
            raise RuntimeError("Can't overwrite with QUEUED run.")
        self.run_entry = {
            "experiment": dict(ex_info),
            "command": command,
            "host": dict(host_info),
            "config": flatten(config),
            "meta": meta_info,
            "status": "QUEUED",
        }
        # set ID if given
        if _id is not None:
            self.run_entry["_id"] = _id
        # save sources
        self.run_entry["experiment"]["sources"] = self.save_sources(ex_info)
        self.insert()
        return self.run_entry["_id"]

    def started_event(
        self, ex_info, command, host_info, start_time, config, meta_info, _id
    ):
        if self.overwrite is None:
            self.run_entry = {"_id": _id}
        else:
            if self.run_entry is not None:
                raise RuntimeError("Cannot overwrite more than once!")
            # TODO sanity checks
            self.run_entry = self.overwrite

        self.run_entry.update(
            {
                "experiment": dict(ex_info),
                "format": self.VERSION,
                "command": command,
                "host": dict(host_info),
                "start_time": start_time,
                "config": flatten(config),
                "meta": meta_info,
                "status": "RUNNING",
                "resources": [],
                "artifacts": [],
                "captured_out": "",
                "info": {},
                "heartbeat": None,
            }
        )

        # save sources
        self.run_entry["experiment"]["sources"] = self.save_sources(ex_info)
        self.insert()
        return self.run_entry["_id"]

    def heartbeat_event(self, info, captured_out, beat_time, result):
        self.run_entry["info"] = flatten(info)
        self.run_entry["captured_out"] = captured_out
        self.run_entry["heartbeat"] = beat_time
        self.run_entry["result"] = flatten(result)
        self.save()

    def completed_event(self, stop_time, result):
        self.run_entry["stop_time"] = stop_time
        self.run_entry["result"] = flatten(result)
        self.run_entry["status"] = "COMPLETED"
        self.final_save(attempts=10)

    def interrupted_event(self, interrupt_time, status):
        self.run_entry["stop_time"] = interrupt_time
        self.run_entry["status"] = status
        self.final_save(attempts=3)

    def failed_event(self, fail_time, fail_trace):
        self.run_entry["stop_time"] = fail_time
        self.run_entry["status"] = "FAILED"
        self.run_entry["fail_trace"] = fail_trace
        self.final_save(attempts=1)

    def resource_event(self, filename):
        if self.fs.exists(filename=filename):
            md5hash = get_digest(filename)
            if self.fs.exists(filename=filename, md5=md5hash):
                resource = (filename, md5hash)
                if resource not in self.run_entry["resources"]:
                    self.run_entry["resources"].append(resource)
                    self.save()
                return
        # Pymongo 4.0: GridFS removed support for md5, we now have to compute
        # it manually
        md5hash = get_digest(filename)
        self.run_entry["resources"].append((filename, md5hash))
        self.save()

    def artifact_event(self, name, filename, metadata=None, content_type=None):
        with open(filename, "rb") as f:
            run_id = self.run_entry["_id"]
            db_filename = "artifact://{}/{}/{}".format(self.runs.name, run_id, name)
            if content_type is None:
                content_type = self._try_to_detect_content_type(filename)

            file_id = self.fs.put(
                f, filename=db_filename, metadata=metadata, content_type=content_type
            )

        self.run_entry["artifacts"].append({"name": name, "file_id": file_id})
        self.save()

    @staticmethod
    def _try_to_detect_content_type(filename):
        mime_type, _ = mimetype_detector.guess_type(filename)
        if mime_type is not None:
            print(
                "Added {} as content-type of artifact {}.".format(mime_type, filename)
            )
        else:
            print(
                "Failed to detect content-type automatically for "
                "artifact {}.".format(filename)
            )
        return mime_type

    def log_metrics(self, metrics_by_name, info):
        """Store new measurements to the database.

        Take measurements and store them into
        the metrics collection in the database.
        Additionally, reference the metrics
        in the info["metrics"] dictionary.
        """
        if self.metrics is None:
            # If, for whatever reason, the metrics collection has not been set
            # do not try to save anything there.
            return
        for key in metrics_by_name:
            query = {"run_id": self.run_entry["_id"], "name": key}
            push = {
                "steps": {"$each": metrics_by_name[key]["steps"]},
                "values": {"$each": metrics_by_name[key]["values"]},
                "timestamps": {"$each": metrics_by_name[key]["timestamps"]},
            }
            update = {"$push": push}
            result = self.metrics.update_one(query, update, upsert=True)
            if result.upserted_id is not None:
                # This is the first time we are storing this metric
                info.setdefault("metrics", []).append(
                    {"name": key, "id": str(result.upserted_id)}
                )

    def insert(self):
        import pymongo.errors

        if self.overwrite:
            return self.save()

        autoinc_key = self.run_entry.get("_id") is None
        while True:
            if autoinc_key:
                c = self.runs.find({}, {"_id": 1})
                c = c.sort("_id", pymongo.DESCENDING).limit(1)
                self.run_entry["_id"] = (
                    c.next()["_id"] + 1 if self.runs.count_documents({}, limit=1) else 1
                )
            try:
                self.runs.insert_one(self.run_entry)
                return
            except pymongo.errors.InvalidDocument as e:
                raise ObserverError(
                    "Run contained an unserializable entry."
                    "(most likely in the info)\n{}".format(e)
                ) from e
            except pymongo.errors.DuplicateKeyError:
                if not autoinc_key:
                    raise

    def save(self):
        import pymongo.errors

        try:
            self.runs.update_one(
                {"_id": self.run_entry["_id"]}, {"$set": self.run_entry}
            )
        except pymongo.errors.AutoReconnect:
            pass  # just wait for the next save
        except pymongo.errors.InvalidDocument as e:
            raise ObserverError(
                "Run contained an unserializable entry." "(most likely in the info)"
            ) from e

    def final_save(self, attempts):
        import pymongo.errors

        for i in range(attempts):
            try:
                self.runs.update_one(
                    {"_id": self.run_entry["_id"]},
                    {"$set": self.run_entry},
                    upsert=True,
                )
                return
            except pymongo.errors.AutoReconnect:
                if i < attempts - 1:
                    time.sleep(1)
            except pymongo.errors.ConnectionFailure:
                pass
            except pymongo.errors.InvalidDocument:
                self.run_entry = force_bson_encodeable(self.run_entry)
                print(
                    "Warning: Some of the entries of the run were not "
                    "BSON-serializable!\n They have been altered such that "
                    "they can be stored, but you should fix your experiment!"
                    "Most likely it is either the 'info' or the 'result'.",
                    file=sys.stderr,
                )

        os.makedirs(self.failure_dir, exist_ok=True)
        with NamedTemporaryFile(
            suffix=".pickle",
            delete=False,
            prefix="sacred_mongo_fail_{}_".format(self.run_entry["_id"]),
            dir=self.failure_dir,
        ) as f:
            pickle.dump(self.run_entry, f)
            print(
                "Warning: saving to MongoDB failed! "
                "Stored experiment entry in '{}'".format(f.name),
                file=sys.stderr,
            )

    def save_sources(self, ex_info):
        base_dir = ex_info["base_dir"]
        source_info = []
        for source_name, md5 in ex_info["sources"]:
            abs_path = os.path.join(base_dir, source_name)
            file = self.fs.find_one({"filename": abs_path, "md5": md5})
            if file:
                _id = file._id
            else:
                with open(abs_path, "rb") as f:
                    _id = self.fs.put(f, filename=abs_path)
            source_info.append([source_name, _id])
        return source_info

    def __eq__(self, other):
        if isinstance(other, MongoObserver):
            return self.runs == other.runs
        return False


@cli_option("-m", "--mongo_db")
def mongo_db_option(args, run):
    """Add a MongoDB Observer to the experiment.

    The argument value is the database specification.
    Should be in the form:

    `[host:port:]db_name[.collection[:id]][!priority]`
    """
    kwargs = parse_mongo_db_arg(args)
    mongo = MongoObserver(**kwargs)
    run.observers.append(mongo)


def get_pattern():
    run_id_pattern = r"(?P<overwrite>\d{1,12})"
    port1_pattern = r"(?P<port1>\d{1,5})"
    port2_pattern = r"(?P<port2>\d{1,5})"
    priority_pattern = r"(?P<priority>-?\d+)?"
    db_name_pattern = r"(?P<db_name>[_A-Za-z]" r"[0-9A-Za-z#%&'()+\-;=@\[\]^_{}]{0,63})"
    coll_name_pattern = (
        r"(?P<collection>[_A-Za-z]" r"[0-9A-Za-z#%&'()+\-;=@\[\]^_{}]{0,63})"
    )
    hostname1_pattern = (
        r"(?P<host1>"
        r"[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?"
        r"(?:\.[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}"
        r"[0-9A-Za-z])?)*)"
    )
    hostname2_pattern = (
        r"(?P<host2>"
        r"[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?"
        r"(?:\.[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}"
        r"[0-9A-Za-z])?)*)"
    )

    host_only = r"^(?:{host}:{port})$".format(
        host=hostname1_pattern, port=port1_pattern
    )
    full = (
        r"^(?:{host}:{port}:)?{db}(?:\.{collection}(?::{rid})?)?"
        r"(?:!{priority})?$".format(
            host=hostname2_pattern,
            port=port2_pattern,
            db=db_name_pattern,
            collection=coll_name_pattern,
            rid=run_id_pattern,
            priority=priority_pattern,
        )
    )

    return r"{host_only}|{full}".format(host_only=host_only, full=full)


def parse_mongo_db_arg(mongo_db):
    g = re.match(get_pattern(), mongo_db).groupdict()
    if g is None:
        raise ValueError(
            'mongo_db argument must have the form "db_name" '
            'or "host:port[:db_name]" but was {}'.format(mongo_db)
        )

    kwargs = {}
    if g["host1"]:
        kwargs["url"] = "{}:{}".format(g["host1"], g["port1"])
    elif g["host2"]:
        kwargs["url"] = "{}:{}".format(g["host2"], g["port2"])

    if g["priority"] is not None:
        kwargs["priority"] = int(g["priority"])

    for p in ["db_name", "collection", "overwrite"]:
        if g[p] is not None:
            kwargs[p] = g[p]

    return kwargs


class QueueCompatibleMongoObserver(MongoObserver):
    def log_metrics(self, metric_name, metrics_values, info):
        """Store new measurements to the database.

        Take measurements and store them into
        the metrics collection in the database.
        Additionally, reference the metrics
        in the info["metrics"] dictionary.
        """
        if self.metrics is None:
            # If, for whatever reason, the metrics collection has not been set
            # do not try to save anything there.
            return
        query = {"run_id": self.run_entry["_id"], "name": metric_name}
        push = {
            "steps": {"$each": metrics_values["steps"]},
            "values": {"$each": metrics_values["values"]},
            "timestamps": {"$each": metrics_values["timestamps"]},
        }
        update = {"$push": push}
        result = self.metrics.update_one(query, update, upsert=True)
        if result.upserted_id is not None:
            # This is the first time we are storing this metric
            info.setdefault("metrics", []).append(
                {"name": metric_name, "id": str(result.upserted_id)}
            )

    def save(self):
        import pymongo

        try:
            self.runs.update_one(
                {"_id": self.run_entry["_id"]}, {"$set": self.run_entry}
            )
        except pymongo.errors.InvalidDocument as exc:
            raise ObserverError(
                "Run contained an unserializable entry. (most likely in the info)"
            ) from exc

    def final_save(self, attempts):
        import pymongo

        try:
            self.runs.update_one(
                {"_id": self.run_entry["_id"]}, {"$set": self.run_entry}, upsert=True
            )
            return

        except pymongo.errors.InvalidDocument:
            self.run_entry = force_bson_encodeable(self.run_entry)
            print(
                "Warning: Some of the entries of the run were not "
                "BSON-serializable!\n They have been altered such that "
                "they can be stored, but you should fix your experiment!"
                "Most likely it is either the 'info' or the 'result'.",
                file=sys.stderr,
            )

            with NamedTemporaryFile(
                suffix=".pickle", delete=False, prefix="sacred_mongo_fail_"
            ) as f:
                pickle.dump(self.run_entry, f)
                print(
                    "Warning: saving to MongoDB failed! "
                    "Stored experiment entry in '{}'".format(f.name),
                    file=sys.stderr,
                )

        raise ObserverError("Warning: saving to MongoDB failed!")


class QueuedMongoObserver(QueueObserver):
    """MongoObserver that uses a fault-tolerant background process."""

    @classmethod
    def create(cls, *args, **kwargs):
        warnings.warn(
            "QueuedMongoObserver.create(...) is deprecated. "
            "Please use QueuedMongoObserver(...) instead.",
            DeprecationWarning,
        )
        return cls(*args, **kwargs)

    def __init__(
        self,
        interval: float = 20.0,
        retry_interval: float = 10.0,
        url: Optional[str] = None,
        db_name: str = "sacred",
        collection: str = "runs",
        overwrite: Optional[Union[int, str]] = None,
        priority: int = DEFAULT_MONGO_PRIORITY,
        client: Optional["pymongo.MongoClient"] = None,
        **kwargs,
    ):
        """Initializer for MongoObserver.

        Parameters
        ----------
        interval
            The interval in seconds at which the background thread is woken up to
            process new events.
        retry_interval
            The interval in seconds to wait if an event failed to be processed.
        url
            Mongo URI to connect to.
        db_name
            Database to connect to.
        collection
            Collection to write the runs to. (default: "runs").
        overwrite
            _id of a run that should be overwritten.
        priority
            (default 30)
        client
            Client to connect to. Do not use client and URL together.
        failure_dir
            Directory to save the run of a failed observer to.
        """
        super().__init__(
            QueueCompatibleMongoObserver(
                url=url,
                db_name=db_name,
                collection=collection,
                overwrite=overwrite,
                priority=priority,
                client=client,
                **kwargs,
            ),
            interval=interval,
            retry_interval=retry_interval,
        )
