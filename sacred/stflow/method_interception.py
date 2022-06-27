from contextlib import ContextDecorator
from .internal import ContextMethodDecorator
import sacred.optional as opt


if opt.has_tensorflow:
    tf = opt.get_tensorflow()
else:
    tf = None


class LogFileWriter(ContextDecorator, ContextMethodDecorator):
    """
    Intercept ``logdir`` each time a new ``FileWriter`` instance is created.

    :param experiment: Tensorflow experiment.

    The state of the experiment must be running when entering the annotated
    function / the context manager.

    When creating ``FileWriters`` in Tensorflow, you might want to
    store the path to the produced log files in the sacred database.

    In the scope of ``LogFileWriter``, the corresponding log directory path
    is appended to a list in experiment.info["tensorflow"]["logdirs"].

    ``LogFileWriter`` can be used both as a context manager or as
     an annotation (decorator) on a function.


    Example usage as decorator::

        ex = Experiment("my experiment")
        @LogFileWriter(ex)
        def run_experiment(_run):
            with tf.Session() as s:
                swr = tf.summary.FileWriter("/tmp/1", s.graph)
                # _run.info["tensorflow"]["logdirs"] == ["/tmp/1"]
                swr2 tf.summary.FileWriter("./test", s.graph)
                #_run.info["tensorflow"]["logdirs"] == ["/tmp/1", "./test"]


    Example usage as context manager::

        ex = Experiment("my experiment")
        def run_experiment(_run):
            with tf.Session() as s:
                with LogFileWriter(ex):
                    swr = tf.summary.FileWriter("/tmp/1", s.graph)
                    # _run.info["tensorflow"]["logdirs"] == ["/tmp/1"]
                    swr3 = tf.summary.FileWriter("./test", s.graph)
                    #_run.info["tensorflow"]["logdirs"] == ["/tmp/1", "./test"]
                # This is called outside the scope and won't be captured
                swr3 = tf.summary.FileWriter("./nothing", s.graph)
                # Nothing has changed:
                #_run.info["tensorflow"]["logdirs"] == ["/tmp/1", "./test"]

    """

    def __init__(self, experiment):
        self.experiment = experiment

        def log_writer_decorator(
            instance, original_method, original_args, original_kwargs
        ):
            result = original_method(instance, *original_args, **original_kwargs)
            if "logdir" in original_kwargs:
                logdir = original_kwargs["logdir"]
            else:
                logdir = original_args[0]
            self.experiment.info.setdefault("tensorflow", {}).setdefault(
                "logdirs", []
            ).append(logdir)
            return result

        ContextMethodDecorator.__init__(
            self, tf.summary.FileWriter, "__init__", log_writer_decorator
        )
