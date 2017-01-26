from functools import wraps
from ..optional import tensorflow


class ContextDecorator():
    """A helper ContextManager decorating a method with a custom function."""

    def __init__(self, classx, method_name, decorator_func):
        """
        Create a new context manager decorating a function within its scope.

        This is a helper Context Manager that decorates a method of a class
        with a custom function.
        The decoration is only valid within the scope.
        :param classx: A class (object)
        :param method_name A string name of the method to be decorated
        :param decorator_func: The decorator function is responsible
         for calling the original method.
         The signature should be: func(instance, original_method,
         original_args, original_kwargs)
         when called, instance refers to an instance of classx and the
         original_method refers to the original method object which can be
         called.
         args and kwargs are arguments passed to the method

        """
        self.method_name = method_name
        self.decorator_func = decorator_func
        self.classx = classx

    def __enter__(self):
        import functools
        self.original_method = getattr(self.classx, self.method_name)

        @functools.wraps(self.original_method)
        def decorated(instance, *args, **kwargs):
            return self.decorator_func(instance, self.original_method, args,
                                       kwargs)

        setattr(self.classx, self.method_name, decorated)

    def __exit__(self, type, value, traceback):
        setattr(self.classx, self.method_name, self.original_method)


class ContextlibDecorator(object):
    "A base class or mixin that enables context managers to work as decorators."

    def _recreate_cm(self):
        """Return a recreated instance of self.

        Allows an otherwise one-shot context manager like
        _GeneratorContextManager to support use as
        a decorator via implicit recreation.

        This is a private interface just for _GeneratorContextManager.
        See issue #11647 (https://bugs.python.org/issue11647) for details.
        """
        return self

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwds):
            with self._recreate_cm():
                return func(*args, **kwds)
        return inner


class LogSummaryWriter(ContextlibDecorator, ContextDecorator):
    """
    Intercept ``logdir`` each time a new ``SummaryWriter`` instance is created.

    :param experiment: Tensorflow experiment.

    The state of the experiment must be running when entering the annotated
    function / the context manager.

    When creating ``SummaryWriters`` in Tensorflow, you might want to
    store the path to the produced log files in the sacred database.

    In the scope of ``LogSummaryWriter``, the corresponding log directory path is
    appended to a list in experiment.info["tensorflow"]["logdirs"].

    ``LogSummaryWriter`` can be used both as a context manager or as an annotation
    (decorator) on a function.


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

        ContextDecorator.__init__(self, tensorflow.train.SummaryWriter, "__init__",
                                  log_writer_decorator)

