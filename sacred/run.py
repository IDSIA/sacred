#!/usr/bin/env python
# coding=utf-8

import datetime
import os.path
import sys
import traceback as tb

from sacred import metrics_logger
from sacred.metrics_logger import linearize_metrics
from sacred.randomness import set_global_seed
from sacred.utils import SacredInterrupt, join_paths, IntervalTimer
from sacred.stdout_capturing import get_stdcapturer


class Run:
    """Represent and manage a single run of an experiment."""

    def __init__(
        self,
        config,
        config_modifications,
        main_function,
        observers,
        root_logger,
        run_logger,
        experiment_info,
        host_info,
        pre_run_hooks,
        post_run_hooks,
        captured_out_filter=None,
    ):

        self._id = None
        """The ID of this run as assigned by the first observer"""

        self.captured_out = ""
        """Captured stdout and stderr"""

        self.config = config
        """The final configuration used for this run"""

        self.config_modifications = config_modifications
        """A ConfigSummary object with information about config changes"""

        self.experiment_info = experiment_info
        """A dictionary with information about the experiment"""

        self.host_info = host_info
        """A dictionary with information about the host"""

        self.info = {}
        """Custom info dict that will be sent to the observers"""

        self.root_logger = root_logger
        """The root logger that was used to create all the others"""

        self.run_logger = run_logger
        """The logger that is used for this run"""

        self.main_function = main_function
        """The main function that is executed with this run"""

        self.observers = observers
        """A list of all observers that observe this run"""

        self.pre_run_hooks = pre_run_hooks
        """List of pre-run hooks (captured functions called before this run)"""

        self.post_run_hooks = post_run_hooks
        """List of post-run hooks (captured functions called after this run)"""

        self.result = None
        """The return value of the main function"""

        self.status = None
        """The current status of the run, from QUEUED to COMPLETED"""

        self.start_time = None
        """The datetime when this run was started"""

        self.stop_time = None
        """The datetime when this run stopped"""

        self.debug = False
        """Determines whether this run is executed in debug mode"""

        self.pdb = False
        """If true the pdb debugger is automatically started after a failure"""

        self.meta_info = {}
        """A custom comment for this run"""

        self.beat_interval = 10.0  # sec
        """The time between two heartbeat events measured in seconds"""

        self.unobserved = False
        """Indicates whether this run should be unobserved"""

        self.force = False
        """Disable warnings about suspicious changes"""

        self.queue_only = False
        """If true then this run will only fire the queued_event and quit"""

        self.captured_out_filter = captured_out_filter
        """Filter function to be applied to captured output"""

        self.fail_trace = None
        """A stacktrace, in case the run failed"""

        self.capture_mode = None
        """Determines the way the stdout/stderr are captured"""

        self._heartbeat = None
        self._failed_observers = []
        self._output_file = None

        self._metrics = metrics_logger.MetricsLogger()

    def open_resource(self, filename, mode="r"):
        """Open a file and also save it as a resource.

        Opens a file, reports it to the observers as a resource, and returns
        the opened file.

        In Sacred terminology a resource is a file that the experiment needed
        to access during a run. In case of a MongoObserver that means making
        sure the file is stored in the database (but avoiding duplicates) along
        its path and md5 sum.

        See also :py:meth:`sacred.Experiment.open_resource`.

        Parameters
        ----------
        filename : str
            name of the file that should be opened
        mode : str
            mode that file will be open

        Returns
        -------
        file
            the opened file-object

        """
        filename = os.path.abspath(filename)
        self._emit_resource_added(filename)  # TODO: maybe non-blocking?
        return open(filename, mode)

    def add_resource(self, filename):
        """Add a file as a resource.

        In Sacred terminology a resource is a file that the experiment needed
        to access during a run. In case of a MongoObserver that means making
        sure the file is stored in the database (but avoiding duplicates) along
        its path and md5 sum.

        See also :py:meth:`sacred.Experiment.add_resource`.

        Parameters
        ----------
        filename : str
            name of the file to be stored as a resource
        """
        filename = os.path.abspath(filename)
        self._emit_resource_added(filename)

    def add_artifact(self, filename, name=None, metadata=None, content_type=None):
        """Add a file as an artifact.

        In Sacred terminology an artifact is a file produced by the experiment
        run. In case of a MongoObserver that means storing the file in the
        database.

        See also :py:meth:`sacred.Experiment.add_artifact`.

        Parameters
        ----------
        filename : str
            name of the file to be stored as artifact
        name : str, optional
            optionally set the name of the artifact.
            Defaults to the filename.
        metadata: dict
            optionally attach metadata to the artifact.
            This only has an effect when using the MongoObserver.
        content_type: str, optional
            optionally attach a content-type to the artifact.
            This only has an effect when using the MongoObserver.
        """
        filename = os.path.abspath(filename)
        name = os.path.basename(filename) if name is None else name
        self._emit_artifact_added(name, filename, metadata, content_type)

    def __call__(self, *args):
        r"""Start this run.

        Parameters
        ----------
        \*args
            parameters passed to the main function

        Returns
        -------
            the return value of the main function

        """
        if self.start_time is not None:
            raise RuntimeError(
                "A run can only be started once. "
                "(Last start was {})".format(self.start_time)
            )

        if self.unobserved:
            self.observers = []
        else:
            self.observers = sorted(self.observers, key=lambda x: -x.priority)

        self.warn_if_unobserved()
        set_global_seed(self.config["seed"])

        if self.capture_mode is None and not self.observers:
            capture_mode = "no"
        else:
            capture_mode = self.capture_mode
        capture_mode, capture_stdout = get_stdcapturer(capture_mode)
        self.run_logger.debug('Using capture mode "%s"', capture_mode)

        if self.queue_only:
            self._emit_queued()
            return
        try:
            with capture_stdout() as self._output_file:
                self._emit_started()
                self._start_heartbeat()
                self._execute_pre_run_hooks()
                self.result = self.main_function(*args)
                self._execute_post_run_hooks()
                if self.result is not None:
                    self.run_logger.info("Result: {}".format(self.result))
                elapsed_time = self._stop_time()
                self.run_logger.info("Completed after %s", elapsed_time)
                self._get_captured_output()
            self._stop_heartbeat()
            self._emit_completed(self.result)
        except (SacredInterrupt, KeyboardInterrupt) as e:
            self._stop_heartbeat()
            status = getattr(e, "STATUS", "INTERRUPTED")
            self._emit_interrupted(status)
            raise
        except BaseException:
            exc_type, exc_value, trace = sys.exc_info()
            self._stop_heartbeat()
            self._emit_failed(exc_type, exc_value, trace.tb_next)
            raise
        finally:
            self._warn_about_failed_observers()
            self._wait_for_observers()

        return self.result

    def _get_captured_output(self):
        if self._output_file.closed:
            return
        text = self._output_file.get()
        if isinstance(text, bytes):
            text = text.decode("utf-8", "replace")
        if self.captured_out:
            text = self.captured_out + text
        if self.captured_out_filter is not None:
            text = self.captured_out_filter(text)
        self.captured_out = text

    def _start_heartbeat(self):
        self.run_logger.debug("Starting Heartbeat")
        if self.beat_interval > 0:
            self._stop_heartbeat_event, self._heartbeat = IntervalTimer.create(
                self._emit_heartbeat, self.beat_interval
            )
            self._heartbeat.start()

    def _stop_heartbeat(self):
        self.run_logger.debug("Stopping Heartbeat")
        # only stop if heartbeat was started
        if self._heartbeat is not None:
            self._stop_heartbeat_event.set()
            self._heartbeat.join(timeout=2)

    def _emit_queued(self):
        self.status = "QUEUED"
        queue_time = datetime.datetime.utcnow()
        self.meta_info["queue_time"] = queue_time
        command = join_paths(
            self.main_function.prefix, self.main_function.signature.name
        )
        self.run_logger.info("Queuing-up command '%s'", command)
        for observer in self.observers:
            if hasattr(observer, "queued_event"):
                _id = observer.queued_event(
                    ex_info=self.experiment_info,
                    command=command,
                    host_info=self.host_info,
                    queue_time=queue_time,
                    config=self.config,
                    meta_info=self.meta_info,
                    _id=self._id,
                )
                if self._id is None:
                    self._id = _id
                # do not catch any exceptions on startup:
                # the experiment SHOULD fail if any of the observers fails

        if self._id is None:
            self.run_logger.info("Queued")
        else:
            self.run_logger.info('Queued-up run with ID "{}"'.format(self._id))

    def _emit_started(self):
        self.status = "RUNNING"
        self.start_time = datetime.datetime.utcnow()
        command = join_paths(
            self.main_function.prefix, self.main_function.signature.name
        )
        self.run_logger.info("Running command '%s'", command)
        for observer in self.observers:
            if hasattr(observer, "started_event"):
                _id = observer.started_event(
                    ex_info=self.experiment_info,
                    command=command,
                    host_info=self.host_info,
                    start_time=self.start_time,
                    config=self.config,
                    meta_info=self.meta_info,
                    _id=self._id,
                )
                if self._id is None:
                    self._id = _id
                # do not catch any exceptions on startup:
                # the experiment SHOULD fail if any of the observers fails
        if self._id is None:
            self.run_logger.info("Started")
        else:
            self.run_logger.info('Started run with ID "{}"'.format(self._id))

    def _emit_heartbeat(self):
        beat_time = datetime.datetime.utcnow()
        self._get_captured_output()
        # Read all measured metrics since last heartbeat
        logged_metrics = self._metrics.get_last_metrics()
        metrics_by_name = linearize_metrics(logged_metrics)
        for observer in self.observers:
            self._safe_call(
                observer, "log_metrics", metrics_by_name=metrics_by_name, info=self.info
            )
            self._safe_call(
                observer,
                "heartbeat_event",
                info=self.info,
                captured_out=self.captured_out,
                beat_time=beat_time,
                result=self.result,
            )

    def _stop_time(self):
        self.stop_time = datetime.datetime.utcnow()
        elapsed_time = datetime.timedelta(
            seconds=round((self.stop_time - self.start_time).total_seconds())
        )
        return elapsed_time

    def _emit_completed(self, result):
        self.status = "COMPLETED"
        for observer in self.observers:
            self._final_call(
                observer, "completed_event", stop_time=self.stop_time, result=result
            )

    def _emit_interrupted(self, status):
        self.status = status
        elapsed_time = self._stop_time()
        self.run_logger.warning("Aborted after %s!", elapsed_time)
        for observer in self.observers:
            self._final_call(
                observer,
                "interrupted_event",
                interrupt_time=self.stop_time,
                status=status,
            )

    def _emit_failed(self, exc_type, exc_value, trace):
        self.status = "FAILED"
        elapsed_time = self._stop_time()
        self.run_logger.error("Failed after %s!", elapsed_time)
        self.fail_trace = tb.format_exception(exc_type, exc_value, trace)
        for observer in self.observers:
            self._final_call(
                observer,
                "failed_event",
                fail_time=self.stop_time,
                fail_trace=self.fail_trace,
            )

    def _emit_resource_added(self, filename):
        for observer in self.observers:
            self._safe_call(observer, "resource_event", filename=filename)

    def _emit_artifact_added(self, name, filename, metadata, content_type):
        for observer in self.observers:
            self._safe_call(
                observer,
                "artifact_event",
                name=name,
                filename=filename,
                metadata=metadata,
                content_type=content_type,
            )

    def _safe_call(self, obs, method, **kwargs):
        if obs not in self._failed_observers and hasattr(obs, method):
            try:
                getattr(obs, method)(**kwargs)
            except Exception as e:
                self._failed_observers.append(obs)
                self.run_logger.warning(
                    "An error ocurred in the '{}' " "observer: {}".format(obs, e)
                )

    def _final_call(self, observer, method, **kwargs):
        if hasattr(observer, method):
            try:
                getattr(observer, method)(**kwargs)
            except Exception:
                # Feels dirty to catch all exceptions, but it is just for
                # finishing up, so we don't want one observer to kill the
                # others
                self.run_logger.error(tb.format_exc())

    def _wait_for_observers(self):
        """Block until all observers finished processing."""
        for observer in self.observers:
            self._safe_call(observer, "join")

    def _warn_about_failed_observers(self):
        for observer in self._failed_observers:
            self.run_logger.warning(
                "The observer '{}' failed at some point "
                "during the run.".format(observer)
            )

    def _execute_pre_run_hooks(self):
        for pr in self.pre_run_hooks:
            pr()

    def _execute_post_run_hooks(self):
        for pr in self.post_run_hooks:
            pr()

    def warn_if_unobserved(self):
        if not self.observers and not self.debug and not self.unobserved:
            self.run_logger.warning("No observers have been added to this run")

    def log_scalar(self, metric_name, value, step=None):
        """
        Add a new measurement.

        The measurement will be processed by the MongoDB observer
        during a heartbeat event.
        Other observers are not yet supported.

        :param metric_name: The name of the metric, e.g. training.loss
        :param value: The measured value
        :param step: The step number (integer), e.g. the iteration number
                    If not specified, an internal counter for each metric
                    is used, incremented by one.
        """
        # Method added in change https://github.com/chovanecm/sacred/issues/4
        # The same as Experiment.log_scalar (if something changes,
        # update the docstring too!)

        self._metrics.log_scalar_metric(metric_name, value, step)
