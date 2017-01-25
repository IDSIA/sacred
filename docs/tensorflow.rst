Integration with Tensorflow
***************************

Sacred provides ways to intereact with the Tensorflow_ library.
The goal is to provide an API to track certain information about
how Tensorflow is used with Sacred. The collected data are stored
in ``experiment.info["tensorflow"]`` where they can be accessed
by various :doc:`observers <observers>`.

Storing Tensorflow logs
-----------------------
It is possible to store Tensorflow summaries paths (created by
``tensorflow.train.SummaryWriter``) into the database under ``info
.tensorflow.logdirs``. This is done automatically whenever a new
``SummaryWriter`` instantiation is detected, provided that the
instantiation occurs within a scope
of a function  method annotated with ``LogSummaryWriter(ex)``
or the code is run inside ``with LogSummaryWriter(ex):`` context.

Example usage as decorator
...........................

.. code-block:: python

    from sacred.tensorflow_hooks import LogSummaryWriter
    from sacred import Experiment
    import tensorflow as tf

    ex = Experiment("my experiment")

    @ex.automain
    @LogSummaryWriter(ex)
    def run_experiment(_run):
        with tf.Session() as s:
            swr = tf.train.SummaryWriter("/tmp/1", s.graph)
            # _run.info["tensorflow"]["logdirs"] == ["/tmp/1"]
            swr2 tf.train.SummaryWriter("./test", s.graph)
            #_run.info["tensorflow"]["logdirs"] == ["/tmp/1", "./test"]



Example usage as context manager
.................................

.. code-block:: python

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
.. _Tensorflow: http://www.tensorflow.org/