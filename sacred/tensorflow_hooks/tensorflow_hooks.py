from ..optional import tensorflow
import wrapt


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


def log_summary_writer(experiment):
    """
    Intercept ``logdir`` each time a new ``SummaryWriter`` instance is created.

    Inside the annotated function, the corresponding log directory path is
    appended to the list in experiment.info["tensorflow"]["logdirs"].

    :param experiment: Tensorflow experiment. The state of the experiment
    must be running when entering the annotated
    function.

    Example:
    ex = Experiment("my experiment")
    @log_summary_writer(ex)
    def run_experiment(_run):
        with tf.Session() as s:
            swr = tf.train.SummaryWriter("/tmp/1", s.graph)
            # _run.info["tensorflow"]["logdirs"] == ["/tmp/1"]
            swr2 tf.train.SummaryWriter("./test", s.graph)
            #_run.info["tensorflow"]["logdirs"] == ["/tmp/1", "./test"]
    """
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        def log_writer_decorator(instance, original_method, original_args,
                                 original_kwargs):
            result = original_method(instance, *original_args,
                                     **original_kwargs)
            if "logdir" in original_kwargs:
                logdir = original_kwargs["logdir"]
            else:
                logdir = original_args[0]
            experiment.info.setdefault("tensorflow", {}).setdefault(
                "logdirs", []).append(logdir)
            return result

        with ContextDecorator(tensorflow.train.SummaryWriter, "__init__",
                              log_writer_decorator):
            return wrapped(*args, **kwargs)
    return wrapper
