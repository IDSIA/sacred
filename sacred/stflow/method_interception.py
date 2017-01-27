from .contextlibbackport import ContextDecorator
from .internal import ContextMethodDecorator
from ..optional import tensorflow


class LogSummaryWriter(ContextDecorator, ContextMethodDecorator):
    """
    Intercept ``logdir`` each time a new ``SummaryWriter`` instance is created.

    :param experiment: Tensorflow experiment.

    The state of the experiment must be running when entering the annotated
    function / the context manager.

    When creating ``SummaryWriters`` in Tensorflow, you might want to
    store the path to the produced log files in the sacred database.

    In the scope of ``LogSummaryWriter``, the corresponding log directory path
    is appended to a list in experiment.info["tensorflow"]["logdirs"].

    ``LogSummaryWriter`` can be used both as a context manager or as
     an annotation (decorator) on a function.


    Example usage as decorator::

        ex = Experiment("my experiment")
        @LogSummaryWriter(ex)
        def run_experiment(_run):
            with tf.Session() as s:
                swr = tf.train.SummaryWriter("/tmp/1", s.graph)
                # _run.info["tensorflow"]["logdirs"] == ["/tmp/1"]
                swr2 tf.train.SummaryWriter("./test", s.graph)
                #_run.info["tensorflow"]["logdirs"] == ["/tmp/1", "./test"]


    Example usage as context manager::

        ex = Experiment("my experiment")
        def run_experiment(_run):
            with tf.Session() as s:
                with LogSummaryWriter(ex):
                    swr = tf.train.SummaryWriter("/tmp/1", s.graph)
                    # _run.info["tensorflow"]["logdirs"] == ["/tmp/1"]
                    swr3 = tf.train.SummaryWriter("./test", s.graph)
                    #_run.info["tensorflow"]["logdirs"] == ["/tmp/1", "./test"]
                # This is called outside the scope and won't be captured
                swr3 = tf.train.SummaryWriter("./nothing", s.graph)
                # Nothing has changed:
                #_run.info["tensorflow"]["logdirs"] == ["/tmp/1", "./test"]

    """

    def __init__(self, experiment):
        self.experiment = experiment

        def log_writer_decorator(instance, original_method, original_args,
                                 original_kwargs):
            result = original_method(instance, *original_args,
                                     **original_kwargs)
            if "logdir" in original_kwargs:
                logdir = original_kwargs["logdir"]
            else:
                logdir = original_args[0]
            self.experiment.info.setdefault("tensorflow", {}).setdefault(
                "logdirs", []).append(logdir)
            return result

        ContextMethodDecorator.__init__(self,
                                        tensorflow.train.SummaryWriter,
                                        "__init__",
                                        log_writer_decorator)
