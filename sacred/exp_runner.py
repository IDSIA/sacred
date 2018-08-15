"""

"""
from __future__ import absolute_import
from __future__ import print_function

import copy
import importlib
import logging
import optparse
import os
import signal
import socket
import subprocess
import sys
import time
from contextlib import contextmanager

import numpy
from future import standard_library

from sacred.observers import MongoObserver

__authors__ = ["Bas Veeling","James Bergstra", "Dan Yamins"]
__license__ = "3-clause BSD License" # TODO: figure out

standard_library.install_aliases()
logger = logging.getLogger(__name__)



class Shutdown(Exception):
    """
    Exception for telling mongo_worker loop to quit
    """


class WaitQuit(Exception):
    """
    Exception for telling mongo_worker loop to quit
    """


class ReserveTimeout(Exception):
    """No job was reserved in the alotted time
    """


class SacredWorker(object):
    poll_interval = 3.0  # -- seconds
    workdir = None

    def __init__(self, observer,
                 poll_interval=poll_interval,
                 workdir=workdir,
                 exp_key=None,
                 logfilename='logfile.txt',
                 ):
        """
        observer - Observer interface to jobs collection
        poll_interval - seconds
        workdir - string
        exp_key - restrict reservations to this key
        """
        self.observer = observer
        self.poll_interval = poll_interval
        self.workdir = workdir
        self.exp_key = exp_key
        self.logfilename = logfilename

    def make_log_handler(self):
        self.log_handler = logging.FileHandler(self.logfilename)
        self.log_handler.setFormatter(
            logging.Formatter(
                fmt='%(levelname)s (%(name)s): %(message)s'))
        self.log_handler.setLevel(logging.INFO)

    def run_one(self,
                host_id=None,
                reserve_timeout=None,
                query=None,
                ):
        if host_id == None:
            host_id = '%s:%i' % (socket.gethostname(), os.getpid()),

        q = copy.copy(query or {})
        # q['_id'] = {'$nin': sorted(blacklist)} # TODO: reinstate blacklist
        run = None
        start_time = time.time()
        observer = self.observer
        while run is None:
                if (reserve_timeout and
                        (time.time() - start_time) > reserve_timeout):
                    raise ReserveTimeout()

                run = observer.find_queued(q)

                if not run:
                    interval = (1 +
                                numpy.random.rand() *
                                (float(self.poll_interval) - 1.0))
                    logger.info('no job found, sleeping for %.1fs' % interval)
                    time.sleep(interval)
        try:
            old_status, run_id = run['status'], run['_id']
            logger.debug('run found: %s' % str(run_id))

            main_file = run['experiment']['mainfile']
            main_module = os.path.splitext(main_file)[0]
            logger.info('Main module: %s' % str(main_module))

            mod = importlib.import_module('%s' % main_module)
            ex = mod.ex

            # ex.observers.clear()
            # ex.observers = [o for o in ex.observers if not isinstance(o, MongoObserver)]
            assert isinstance(ex.observers[0], MongoObserver)
            ex.observers[0] = observer
            # Done:
        except BaseException as e:
            observer.requeue(run)
            raise e
        else:
            result = ex.run_command(run['command'],run['config'])
            logger.info('job finished: %s' % str(run['_id']))
@contextmanager
def working_dir(dir):
    cwd = os.getcwd()
    os.chdir(dir)
    yield
    os.chdir(cwd)

def exec_import(cmd_module, cmd):
    worker_fn = None
    exec('import %s; worker_fn = %s' % (cmd_module, cmd))
    return worker_fn


def as_mongo_str(s):
    if s.startswith('mongodb://'):
        return s
    else:
        return 'mongodb://%s' % s


def main_worker_helper(options, args):
    N = int(options.max_jobs)
    if options.last_job_timeout is not None:
        last_job_timeout = time.time() + float(options.last_job_timeout)
    else:
        last_job_timeout = None

    def sighandler_shutdown(signum, frame):
        logger.info('Caught signal %i, shutting down.' % signum)
        raise Shutdown(signum)

    def sighandler_wait_quit(signum, frame):
        logger.info('Caught signal %i, shutting down.' % signum)
        raise WaitQuit(signum)

    signal.signal(signal.SIGINT, sighandler_shutdown)
    signal.signal(signal.SIGHUP, sighandler_shutdown)
    signal.signal(signal.SIGTERM, sighandler_shutdown)
    signal.signal(signal.SIGUSR1, sighandler_wait_quit)

    if N > 1:
        proc = None
        cons_errs = 0
        if last_job_timeout and time.time() > last_job_timeout:
            logger.info("Exiting due to last_job_timeout")
            return

        while N and cons_errs < int(options.max_consecutive_failures):
            try:
                # recursive Popen, dropping N from the argv
                # By using another process to run this job
                # we protect ourselves from memory leaks, bad cleanup
                # and other annoying details.
                # The tradeoff is that a large dataset must be reloaded once for
                # each subprocess.
                sub_argv = [sys.argv[0],
                            '--poll-interval=%s' % options.poll_interval,
                            '--max-jobs=1',
                            '--mongo=%s' % options.mongo,
                            '--db_name=%s' % options.db_name,
                            '--reserve-timeout=%s' % options.reserve_timeout]
                if options.workdir is not None:
                    sub_argv.append('--workdir=%s' % options.workdir)
                if options.exp_key is not None:
                    sub_argv.append('--exp-key=%s' % options.exp_key)
                proc = subprocess.Popen(sub_argv)
                retcode = proc.wait()
                proc = None

            except Shutdown:
                # this is the normal way to stop the infinite loop (if originally N=-1)
                if proc:
                    # proc.terminate() is only available as of 2.6
                    os.kill(proc.pid, signal.SIGTERM)
                    return proc.wait()
                else:
                    return 0

            except WaitQuit:
                # -- sending SIGUSR1 to a looping process will cause it to
                # break out of the loop after the current subprocess finishes
                # normally.
                if proc:
                    return proc.wait()
                else:
                    return 0

            if retcode != 0:
                cons_errs += 1
            else:
                cons_errs = 0
            N -= 1
        logger.info("exiting with N=%i after %i consecutive exceptions" % (
            N, cons_errs))
    elif N == 1:
        # XXX: the name of the jobs collection is a parameter elsewhere,
        #      so '/jobs' should not be hard-coded here
        observer = MongoObserver.create(as_mongo_str(options.mongo), db_name=options.db_name)
        # mj = MongoJobs.new_from_connection_str(
        #     as_mongo_str(options.mongo) + '/jobs')

        mworker = SacredWorker(observer,
                               float(options.poll_interval),
                               workdir=options.workdir,
                               exp_key=options.exp_key)
        mworker.run_one(reserve_timeout=float(options.reserve_timeout))
    else:
        raise ValueError("N <= 0")


def main_worker():
    parser = optparse.OptionParser(usage="%prog [options]")

    parser.add_option("--exp-key",
                      dest='exp_key',
                      default=None,
                      metavar='str',
                      help="identifier for this workers's jobs")
    parser.add_option("--last-job-timeout",
                      dest='last_job_timeout',
                      metavar='T',
                      default=None,
                      help="Do not reserve a job after T seconds have passed")
    parser.add_option("--max-consecutive-failures",
                      dest="max_consecutive_failures",
                      metavar='N',
                      default=4,
                      help="stop if N consecutive jobs fail (default: 4)")
    parser.add_option("--max-jobs",
                      dest='max_jobs',
                      default=sys.maxsize,
                      help="stop after running this many jobs (default: inf)")
    parser.add_option("--mongo",
                      dest='mongo',
                      default='localhost',
                      help="<host>[:port]/<db> for IPC and job storage")
    parser.add_option("--db_name",
                      dest='db_name',
                      default='sacred',
                      help="db name")
    parser.add_option("--poll-interval",
                      dest='poll_interval',
                      metavar='N',
                      default=5,
                      help="check work queue every 1 < T < N seconds (default: 5")
    parser.add_option("--reserve-timeout",
                      dest='reserve_timeout',
                      metavar='T',
                      default=0,
                      help="poll database for up to T seconds to reserve a job")
    parser.add_option("--workdir",
                      dest="workdir",
                      default=None,
                      help="root workdir (default: load from mongo)",
                      metavar="DIR")

    (options, args) = parser.parse_args()

    if args:
        parser.print_help()
        return -1

    return main_worker_helper(options, args)


