Integration with Tensorflow
***************************

Sacred provides ways to interact with the Tensorflow_ library.
The goal is to provide an API to track certain information about
how Tensorflow is used with Sacred. The collected data are stored
in ``experiment.info["tensorflow"]`` where they can be accessed
by various :doc:`observers <observers>`.

Storing Tensorflow logs
-----------------------
It is possible to store Tensorflow summaries paths (created by
``tensorflow.summary.FileWriter``) into the database under
``info.tensorflow.logdirs``. This is done automatically whenever a new
``FileWriter`` instantiation is detected, provided that the
instantiation occurs within a scope
of a function  method annotated with ``LogFileWriter(ex)``
or the code is run inside ``with LogFileWriter(ex):`` context.

Example usage as decorator
...........................

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



Example usage as context manager
.................................

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