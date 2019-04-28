#!/usr/bin/env python
# coding=utf-8
"""This module defines experiments with duplication checking."""
from __future__ import division, print_function, unicode_literals

from sacred.experiment import Experiment

__all__ = ('DuplicateChecker', 'DuplicateCheckerMongo', 'DuplicateError',
  'NoDuplicateExperiment', )

class DuplicateError(RuntimeError):
  def __init__(*args, **kwargs):
    self.info = None

class NoDuplicateExperiment(Experiment):
  def __init__(self, *args, duplicate_checker = None,
      ignored_params = None, **kwargs):
    super().__init__(*args, **kwargs)
    self._duplicate_checker = duplicate_checker
    self._ignored_params = ignored_params
    self.pre_run_hook(
      lambda run, logger:
        self._prerun_hook_check_duplicate(run, logger))
    self.option_hook(lambda options: self._option_hook_add_md5(options))
  
  def _option_hook_add_md5(self, options):
    options['--md5'] = True
    if not self._ignored_params is None:
      options['--md5_ignore'] = ','.join(self._ignored_params)

  def _prerun_hook_check_duplicate(self, run, logger):
    if self._duplicate_checker is None:
      logger.warning('empty duplicate checker, cannot check for duplicates!')
      return
    exception = DuplicateError()
    dupe = self._duplicate_checker.check_duplicate(run, logger, exception)
    if dupe > -1:
      exception.args = ('Experiment already run, id={:d}!'.format(dupe), )
      raise exception

class DuplicateChecker(object):
  def check_duplicate(self, run, logger, exception):
    return -1

class DuplicateCheckerMongo(DuplicateChecker):
  def __init__(self, host, port, collection, *args, **kwargs):
    super().__init__(*args, **kwargs)
    from pymongo import MongoClient
    self.client = MongoClient(host, port)
    self.collection = self.client[collection]

  def check_duplicate(self, run, logger, exception):
    runs = tuple(
      self.collection.runs.find({'meta.md5': run.meta_info['md5']}))
    if len(runs) > 0:
      exception.info = runs
      found = runs[-1]['_id']
    else:
      found = -1
    return found
