Integration with Tensorflow
***************************

Sacred provides ways to interact with the Tensorflow_ library.
The goal is to provide an API that would allow tracking certain
information about how Tensorflow is being used with Sacred.
The collected data are stored in ``experiment.info["tensorflow"]``
where they can be accessed by various :doc:`observers <observers>`.

Storing Tensorflow Logs (FileWriter)
------------------------------------

To store the location of summaries produced by Tensorflow
(created by ``tensorflow.summary.FileWriter``) into the experiment record
specified by the ``ex`` argument, use the ``sacred.stflow.LogFileWriter(ex)``
decorator or context manager.
Whenever a new ``FileWriter`` instantiation is detected in a scope of the
decorator or the context manager, the path of the log is
copied to the experiment record exactly as passed to the FileWriter.

The location(s) can be then found under ``info["tensorflow"]["logdirs"]``
of the experiment.

**Important**: The experiment must be in the *RUNNING* state before calling
the decorated method or entering the context.


Example Usage As a Decorator
............................

``LogFileWriter(ex)`` as a decorator can be used either on a function or
on a class method.

.. code-block:: python

    from sacred.stflow import LogFileWriter
    from sacred import Experiment
    import tensorflow as tf

    ex = Experiment("my experiment")

    @ex.automain
    @LogFileWriter(ex)
    def run_experiment(_run):
        with tf.Session() as s:
            swr = tf.summary.FileWriter("/tmp/1", s.graph)
            # _run.info["tensorflow"]["logdirs"] == ["/tmp/1"]
            swr2 = tf.summary.FileWriter("./test", s.graph)
            #_run.info["tensorflow"]["logdirs"] == ["/tmp/1", "./test"]



Example Usage As a Context Manager
..................................

There is a context manager available to catch the paths
in a smaller portion of code.

.. code-block:: python

        ex = Experiment("my experiment")
        def run_experiment(_run):
            with tf.Session() as s:
                with LogFileWriter(ex):
                    swr = tf.summary.FileWriter("/tmp/1", s.graph)
                    # _run.info["tensorflow"]["logdirs"] == ["/tmp/1"]
                    swr3 = tf.summary.FileWriter("./test", s.graph)
                    # _run.info["tensorflow"]["logdirs"] == ["/tmp/1", "./test"]
                # This is called outside the scope and won't be captured
                swr3 = tf.summary.FileWriter("./nothing", s.graph)
                # Nothing has changed:
                # _run.info["tensorflow"]["logdirs"] == ["/tmp/1", "./test"]
.. _Tensorflow: http://www.tensorflow.org/