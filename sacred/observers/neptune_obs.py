#!/usr/bin/env python
# coding=utf-8

import collections
import os

import neptune
from sacred.dependencies import get_digest
from sacred.observers import RunObserver


class NeptuneObserver(RunObserver):
    """Logs sacred experiment data to Neptune.

    Sacred observer that logs experiment metadata to neptune.ml app.
    The experiment data can be accessed and shared via web UI or experiment API.
    Check Neptune docs for more information https://docs.neptune.ml.

    Args:
        project_name(str): project name in Neptune app
        api_token(str): Neptune API token. If it is kept in the NEPTUNE_API_TOKEN environment
           variable leave None here.
        base_dir(str): base directory from which you run your code.
        source_extensions(list(str)): list of extensions that Neptune should treat as source files
           extensions and send.

    Examples:
        Create sacred experiment::

            from numpy.random import permutation
            from sklearn import svm, datasets
            from sacred import Experiment

            ex = Experiment('iris_rbf_svm')

        Add Neptune observer::

            from neptunecontrib.monitoring.sacred import NeptuneObserver
            ex.observers.append(NeptuneObserver(api_token='YOUR_LONG_API_TOKEN',
                                                project_name='USER_NAME/PROJECT_NAME'))

        Run experiment::

            @ex.config
            def cfg():
                C = 1.0
                gamma = 0.7

            @ex.automain
            def run(C, gamma, _run):
                iris = datasets.load_iris()
                per = permutation(iris.target.size)
                iris.data = iris.data[per]
                iris.target = iris.target[per]
                clf = svm.SVC(C, 'rbf', gamma=gamma)
                clf.fit(iris.data[:90],
                        iris.target[:90])
                return clf.score(iris.data[90:],
                                 iris.target[90:])

        Go to the app and see the experiment. For example, https://ui.neptune.ml/jakub-czakon/examples/e/EX-263
    """

    def __init__(self, project_name, api_token=None, base_dir='.', source_extensions=None):
        neptune.init(project_qualified_name=project_name, api_token=api_token)
        self.resources = {}
        self.base_dir = base_dir
        if source_extensions:
            self.source_extensions = source_extensions
        else:
            self.source_extensions = ['.py', '.R', '.cpp', '.yaml', '.yml']

    def started_event(self, ex_info, command, host_info, start_time, config, meta_info, _id):

        neptune.create_experiment(name=ex_info['name'],
                                  params=_flatten_dict(config),
                                  upload_source_files=_get_filepaths(dirpath=self.base_dir,
                                                                     extensions=self.source_extensions),
                                  properties={'mainfile': ex_info['mainfile'],
                                              'dependencies': str(ex_info['dependencies']),
                                              'sacred_id': str(_id),
                                              **_str_dict_values(host_info),
                                              **_str_dict_values(_flatten_dict(meta_info))})

    def completed_event(self, stop_time, result):
        if result:
            neptune.log_metric('result', result)
        neptune.stop()

    def interrupted_event(self, interrupt_time, status):
        neptune.stop()

    def failed_event(self, fail_time, fail_trace):
        neptune.stop()

    def artifact_event(self, name, filename, metadata=None, content_type=None):
        neptune.log_artifact(filename)

    def resource_event(self, filename):
        if filename not in self.resources:
            new_prefix = self._create_new_prefix()
            self.resources[filename] = new_prefix
            md5 = get_digest(filename)

            neptune.set_property('{}data_path'.format(new_prefix), filename)
            neptune.set_property('{}data_version'.format(new_prefix), md5)

    def log_metrics(self, metrics_by_name, info):
        for metric_name, metric_ptr in metrics_by_name.items():
            for step, value in zip(metric_ptr["steps"], metric_ptr["values"]):
                neptune.log_metric(metric_name, x=step, y=value)

    def _create_new_prefix(self):
        existing_prefixes = self.resources.values()
        if existing_prefixes:
            prefix_ids = [int(prefix.replace('resource', '')) for prefix in existing_prefixes]
            new_prefix = 'resource{}'.format(max(prefix_ids) + 1)
        else:
            new_prefix = 'resource0'
        return new_prefix


def _get_filepaths(dirpath, extensions):
    files = []
    for r, _, f in os.walk(dirpath):
        for file in f:
            if any(file.endswith(ext) for ext in extensions):
                files.append(os.path.join(r, file))
    return files


def _flatten_dict(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def _str_dict_values(d):
    return {k: str(v) for k, v in d.items()}
