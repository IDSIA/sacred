# -*- coding: utf8 -*-
import pytest

from sacred import Experiment
from sacred.stflow import LogSummaryWriter


@pytest.fixture
def ex():
    return Experiment('tensorflow_tests')


# Creates a simplified tensorflow interface if necessary
# so tensorflow is not required during the tests
@pytest.fixture()
def tf():
    from sacred.optional import has_tensorflow, tensorflow
    if has_tensorflow:
        return tensorflow
    else:
        # Let's define a mocked tensorflow
        class tensorflow():
            class train():
                class SummaryWriter():
                    def __init__(self, logdir, graph):
                        self.logdir = logdir
                        self.graph = graph
                        print("Mocked SummaryWriter got logdir=%s, graph=%s" % (logdir, graph))

            class Session():
                def __init__(self):
                    self.graph = None

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass

        # Set stflow to use the mock as the test
        import sacred.stflow.method_interception
        sacred.stflow.method_interception.tensorflow = tensorflow
        return tensorflow


# Tests whether logdir is stored into the info dictionary when creating a new SummaryWriter object
def test_log_summary_writer(ex, tf):
    TEST_LOG_DIR = "/dev/null"
    TEST_LOG_DIR2 = "/tmp/sacred_test"

    @ex.main
    @LogSummaryWriter(ex)
    def run_experiment(_run):
        assert _run.info.get("tensorflow", None) is None
        with tf.Session() as s:
            swr = tf.train.SummaryWriter(logdir=TEST_LOG_DIR, graph=s.graph)
            assert swr is not None
            assert _run.info["tensorflow"]["logdirs"] == [TEST_LOG_DIR]
            tf.train.SummaryWriter(TEST_LOG_DIR2, s.graph)
            assert _run.info["tensorflow"]["logdirs"] == [TEST_LOG_DIR, TEST_LOG_DIR2]

    ex.run()


def test_log_summary_writer_as_context_manager(ex, tf):
    """ Check that Tensorflow log directory is captured by LogSummaryWriter context manager"""
    TEST_LOG_DIR = "/dev/null"
    TEST_LOG_DIR2 = "/tmp/sacred_test"

    @ex.main
    def run_experiment(_run):
        assert _run.info.get("tensorflow", None) is None
        with tf.Session() as s:
            # Without using the LogSummaryWriter context manager, nothing should change
            swr = tf.train.SummaryWriter(logdir=TEST_LOG_DIR, graph=s.graph)
            assert swr is not None
            assert _run.info.get("tensorflow", None) is None

            # Capturing the log directory should be done only in scope of the context manager
            with LogSummaryWriter(ex):
                swr = tf.train.SummaryWriter(logdir=TEST_LOG_DIR, graph=s.graph)
                assert swr is not None
                assert _run.info["tensorflow"]["logdirs"] == [TEST_LOG_DIR]
                tf.train.SummaryWriter(TEST_LOG_DIR2, s.graph)
                assert _run.info["tensorflow"]["logdirs"] == [TEST_LOG_DIR, TEST_LOG_DIR2]

            # This should not be captured:
            tf.train.SummaryWriter("/tmp/whatever", s.graph)
            assert _run.info["tensorflow"]["logdirs"] == [TEST_LOG_DIR, TEST_LOG_DIR2]

    ex.run()

def test_log_summary_writer_as_context_manager_with_exception(ex, tf):
    """ Check that Tensorflow log directory is captured by LogSummaryWriter context manager"""
    TEST_LOG_DIR = "/tmp/sacred_test"

    @ex.main
    def run_experiment(_run):
        assert _run.info.get("tensorflow", None) is None
        with tf.Session() as s:
            # Capturing the log directory should be done only in scope of the context manager
            try:
                with LogSummaryWriter(ex):
                    swr = tf.train.SummaryWriter(logdir=TEST_LOG_DIR, graph=s.graph)
                    assert swr is not None
                    assert _run.info["tensorflow"]["logdirs"] == [TEST_LOG_DIR]
                    raise ValueError("I want to be raised!")
            except ValueError:
                pass
            # This should not be captured:
            tf.train.SummaryWriter("/tmp/whatever", s.graph)
            assert _run.info["tensorflow"]["logdirs"] == [TEST_LOG_DIR]

    ex.run()

# Tests whether logdir is stored into the info dictionary when creating a new SummaryWriter object,
# but this time on a method of a class
def test_log_summary_writer_class(ex, tf):
    TEST_LOG_DIR = "/dev/null"
    TEST_LOG_DIR2 = "/tmp/sacred_test"

    class FooClass():
        def __init__(self):
            pass

        @LogSummaryWriter(ex)
        def hello(self, argument):
            with tf.Session() as s:
                tf.train.SummaryWriter(argument, s.graph)

    @ex.main
    def run_experiment(_run):
        assert _run.info.get("tensorflow", None) is None
        foo = FooClass()
        with tf.Session() as s:
            swr = tf.train.SummaryWriter(TEST_LOG_DIR, s.graph)
            assert swr is not None
            # Because SummaryWritter was not called in an annotated function
            assert _run.info.get("tensorflow", None) is None
        foo.hello(TEST_LOG_DIR2)
        # Because foo.hello was anotated
        assert _run.info["tensorflow"]["logdirs"] == [TEST_LOG_DIR2]

        with tf.Session() as s:
            swr = tf.train.SummaryWriter(TEST_LOG_DIR, s.graph)
            # Nothing should be added, because SummaryWritter was again not called in an annotated function
            assert _run.info["tensorflow"]["logdirs"] == [TEST_LOG_DIR2]

    ex.run()

