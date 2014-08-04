#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from collections import OrderedDict, defaultdict, namedtuple
from copy import copy
from sacred.custom_containers import dogmatize, undogmatize
from sacred.utils import get_seed, create_rnd, is_prefix, set_by_dotted_path, \
    iterate_flattened, iter_prefixes, iter_path_splits, \
    create_basic_stream_logger, join_paths
from run import Run


class Scaffold(object):
    def __init__(self, config_scopes, subrunners, path, captured_functions,
                 generate_seed):
        self.config_scopes = config_scopes
        self.subrunners = subrunners
        self.path = path
        self.generate_seed = generate_seed
        self.config_updates = {}
        self.config = None
        self.fixture = None  # TODO: rename
        self.logger = None
        self.seed = None
        self.rnd = None
        self._captured_functions = captured_functions

    def set_up_seed(self, rnd=None):
        if self.seed is not None:
            return

        self.seed = self.config_updates.get('seed') or get_seed(rnd)
        self.rnd = create_rnd(self.seed)

        # Hierarchically set the seed of proper subrunners
        for subrunner in reversed(self.subrunners):
            if is_prefix(self.path, subrunner.path):
                subrunner.set_up_seed(self.rnd)

    def set_up_config(self):
        if self.config is not None:
            return self.config

        # gather presets
        fallback = {}
        for sr in self.subrunners:
            if self.path and is_prefix(self.path, sr.path):
                path = sr.path[len(self.path):].strip('.')
                set_by_dotted_path(fallback, path, sr.config)
            else:
                set_by_dotted_path(fallback, sr.path, sr.config)

        # dogmatize to make the subrunner configurations read-only
        const_fallback = dogmatize(fallback)
        const_fallback.revelation()

        self.config = {}

        if self.generate_seed:
            self.config['seed'] = self.seed

        for config in self.config_scopes:
            config(fixed=self.config_updates,
                   preset=self.config,
                   fallback=const_fallback)
            self.config.update(config)

        self.config = undogmatize(self.config)

        return self.config

    def get_config_modifications(self):
        added = set()
        typechanges = {}
        flat_config_upd = [k for k, v in iterate_flattened(self.config_updates)]
        updated = {sp for p in flat_config_upd for sp in iter_prefixes(p)}
        for config in self.config_scopes:
            added |= config.added_values
            typechanges.update(config.typechanges)

        return added, updated, typechanges

    def get_fixture(self):
        if self.fixture is not None:
            return self.fixture

        self.fixture = copy(self.config)
        for sr in self.subrunners:
            sub_fix = sr.get_fixture()
            sub_path = sr.path
            if is_prefix(self.path, sub_path):
                sub_path = sr.path[len(self.path):].strip('.')
            # Note: This might fail if we allow non-dict fixtures
            set_by_dotted_path(self.fixture, sub_path, sub_fix)
        return self.fixture

    def finalize_initialization(self, run):
        # look at seed again, because it might have changed during the
        # configuration process
        if 'seed' in self.config:
            self.seed = self.config['seed']
            self.rnd = create_rnd(self.seed)

        for cf in self._captured_functions:
            cf.logger = self.logger.getChild(cf.__name__)
            cf.config = self.get_fixture()
            cf.seed = get_seed(self.rnd)
            cf.rnd = create_rnd(cf.seed)
            cf.run = run

        self._warn_about_suspicious_changes()

    def _warn_about_suspicious_changes(self, ):
        add, upd, tch = self.get_config_modifications()
        for a in sorted(add):
            self.logger.warning('Added new config entry: "%s"' % a)
        for k, (t1, t2) in tch.items():
            if (isinstance(t1, type(None)) or
                    (t1 in (int, float) and t2 in (int, float))):
                continue
            self.logger.warning(
                'Changed type of config entry "%s" from %s to %s' %
                (k, t1.__name__, t2.__name__))


def get_configuration(scaffolding):
    config = {}
    for sc in reversed(scaffolding):
        if sc.path:
            set_by_dotted_path(config, sc.path, sc.config)
        else:
            config.update(sc.config)
    return config


def distribute_config_updates(scaffolding, config_updates):
    modrunner_cfgups = {sc.path: sc.config_updates for sc in scaffolding}
    for path, value in iterate_flattened(config_updates):
        for p1, p2 in reversed(list(iter_path_splits(path))):
            if p1 in modrunner_cfgups:
                set_by_dotted_path(modrunner_cfgups[p1], p2, value)
                break
                # this is guaranteed to occur for one of the modrunners,
                # because the exrunner has path ''


def initialize_logging(experiment, scaffolding, loglevel=None):
    if experiment.logger is None:
        if loglevel:
            try:
                loglevel = int(loglevel)
            except ValueError:
                pass
        root_logger = create_basic_stream_logger('', level=loglevel)
    else:
        root_logger = experiment.logger
        if loglevel:
            root_logger.setLevel(loglevel)

    for sc in scaffolding:
        sc.logger = root_logger.getChild(sc.path)

    return root_logger.getChild(experiment.name)


def create_scaffolding(experiment):
    sorted_submodules = gather_submodules_topological(experiment)
    scaffolding = OrderedDict()
    for sm in sorted_submodules:
        scaffolding[sm] = Scaffold(
            sm.cfgs,
            subrunners=[scaffolding[m] for m in sm.modules],
            path=sm.path,
            captured_functions=sm.captured_functions,
            generate_seed=sm.gen_seed)
    return scaffolding.values()


def gather_submodules_topological(module):
    submodules = defaultdict(int)
    for sm, depth in module.traverse_modules():
        submodules[sm] = max(submodules[sm], depth)
    return sorted(submodules, key=lambda x: -submodules[x])


ConfigModifications = namedtuple('ConfigModifications',
                                 ['added', 'updated', 'typechanges'])


def get_config_modifications(scaffolding):
    added = set()
    updated = set()
    typechanges = {}
    for sc in scaffolding:
        mr_add, mr_up, mr_tc = sc.get_config_modifications()
        if mr_add or mr_up or mr_tc:
            updated |= set(iter_prefixes(sc.path))
        added |= {join_paths(sc.path, a) for a in mr_add}
        updated |= {join_paths(sc.path, u) for u in mr_up}
        typechanges.update({join_paths(sc.path, k): v
                            for k, v in mr_tc.items()})
    return ConfigModifications(added, updated, typechanges)


def create_run(experiment, config_updates=None, main_func=None, observe=True,
               log_level=None):
    scaffolding = create_scaffolding(experiment)
    logger = initialize_logging(experiment, scaffolding, log_level)

    if config_updates is not None:
        distribute_config_updates(scaffolding, config_updates)

    for sc in reversed(scaffolding):
        sc.set_up_seed()  # partially recursive

    for sc in scaffolding:
        sc.set_up_config()

    config = get_configuration(scaffolding)

    observers = experiment.observers if observe else []
    if main_func is None:
        main_func = experiment.main_function

    config_modifications = get_config_modifications(scaffolding)

    # only get experiment info if there are observers
    experiment_info = experiment.get_info() if observers else dict(
        name=experiment.name,
        mainfile='',
        dependencies=[],
        doc='',
        host_info={}
    )

    run = Run(config, config_modifications, main_func, observers, logger,
              experiment_info)

    for sc in scaffolding:
        sc.finalize_initialization(run=run)

    return run