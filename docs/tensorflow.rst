Integration with Tensorflow
***************************
This is a construction site...

Sacred contains some (currently: one) ways to interact with the Tensorflow_ library.

Storing Tensorflow logs
-----------------------
It is now possible to store Tensorflow summaries paths (created by
``tensorflow.train.SummaryWriter``) into the database under ``info
.tensorflow.logdirs``. This is done automatically whenever a new
``SummaryWriter`` instantiation is detected, provided that the
instantiation occurs within a scope
of a function or method annotated with ``log_summary_writer(ex)``

.. code-block:: python

    from sacred.tensorflow_hooks import log_summary_writer
    from sacred import Experiment
    import tensorflow as tf

    ex = Experiment("my experiment")

    @ex.automain
    @log_summary_writer(ex)
    def run_experiment(_run):
        with tf.Session() as s:
            swr = tf.train.SummaryWriter("/tmp/1", s.graph)
            # _run.info["tensorflow"]["logdirs"] == ["/tmp/1"]
            swr2 tf.train.SummaryWriter("./test", s.graph)
            #_run.info["tensorflow"]["logdirs"] == ["/tmp/1", "./test"]

.. _Tensorflow: http://www.tensorflow.org/