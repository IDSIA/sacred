#!/usr/bin/python
# coding=utf-8

from __future__ import division, print_function, unicode_literals
from collections import OrderedDict, defaultdict, namedtuple
from copy import copy
from sacred.custom_containers import dogmatize, undogmatize
from sacred.host_info import get_host_info
from sacred.run import Run
from sacred.utils import (
    get_seed, create_rnd, is_prefix, set_by_dotted_path, iterate_flattened,
    iter_prefixes, iter_path_splits, create_basic_stream_logger, join_paths,
    get_by_dotted_path, convert_to_nested_dict)


__sacred__ = True  # marker for filtering stacktraces when run from commandline


class Scaffold(object):
    def __init__(self, config_scopes, subrunners, path, captured_functions,
                 commands, named_configs, generate_seed):
        self.config_scopes = config_scopes
        self.named_configs = named_configs
        self.subrunners = subrunners
        self.path = path
        self.generate_seed = generate_seed
        self.config_updates = {}
        self.named_configs_to_use = []
        self.config = None
        self.fixture = None  # TODO: rename
        self.logger = None
        self.seed = None
        self.rnd = None
        self._captured_functions = captured_functions
        self.commands = commands

    def set_up_seed(self, rnd=None):
        if self.seed is not None:
            return

        self.seed = self.config_updates.get('seed') or get_seed(rnd)
        self.rnd = create_rnd(self.seed)

        # Hierarchically set the seed of proper subrunners
        for subrunner_path, subrunner in reversed(list(self.subrunners.items())):
            if is_prefix(self.path, subrunner_path):
                subrunner.set_up_seed(self.rnd)

    def set_up_config(self):
        if self.config is not None:
            return self.config

        # gather presets
        fallback = {}
        for sr_path, sr in self.subrunners.items():
            if self.path and is_prefix(self.path, sr_path):
                path = sr_path[len(self.path):].strip('.')
                set_by_dotted_path(fallback, path, sr.config)
            else:
                set_by_dotted_path(fallback, sr_path, sr.config)

        # dogmatize to make the subrunner configurations read-only
        const_fallback = dogmatize(fallback)
        const_fallback.revelation()

        self.config = {}

        if self.generate_seed:
            self.config['seed'] = self.seed

        # named configs first
        for cfgname in self.named_configs_to_use:
            config = self.named_configs[cfgname]
            config(fixed=self.config_updates,
                   preset=self.config,
                   fallback=const_fallback)
            self.config_updates.update(config)

        # unnamed (default) configs second
        for config in self.config_scopes:
            config(fixed=self.config_updates,
                   preset=self.config,
                   fallback=const_fallback)
            self.config.update(config)

        self.config = undogmatize(self.config)

        return self.config

    def get_config_modifications(self):
        typechanges = {}
        flat_config_upd = [k for k, v in iterate_flattened(self.config_updates)]
        updated = {sp for p in flat_config_upd for sp in iter_prefixes(p)}
        added = set(updated)
        for config in self.config_scopes:
            added &= config.added_values
            typechanges.update(config.typechanges)

        return added, updated, typechanges

    def get_fixture(self):
        if self.fixture is not None:
            return self.fixture

        self.fixture = copy(self.config)
        for sr_path, sr in self.subrunners.items():
            sub_fix = sr.get_fixture()
            sub_path = sr_path
            if is_prefix(self.path, sub_path):
                sub_path = sr_path[len(self.path):].strip('.')
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
            cf.config = get_by_dotted_path(self.get_fixture(), cf.prefix)
            seed = get_seed(self.rnd)
            cf.rnd = create_rnd(seed)
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
    for sc_path, sc in reversed(list(scaffolding.items())):
        if sc_path:
            set_by_dotted_path(config, sc_path, sc.config)
        else:
            config.update(sc.config)
    return config


def distribute_config_updates(scaffolding, config_updates):
    if config_updates is None:
        return
    nested_config_updates = convert_to_nested_dict(config_updates)
    for path, value in iterate_flattened(nested_config_updates):
        for p1, p2 in reversed(list(iter_path_splits(path))):
            if p1 in scaffolding:
                set_by_dotted_path(scaffolding[p1].config_updates, p2, value)
                break
                # this is guaranteed to occur for one of the modrunners,
                # because the exrunner has path ''


def distribute_named_configs(scaffolding, named_configs):
    for ncfg in named_configs:
        path, _, cfg_name = ncfg.rpartition('.')
        if path not in scaffolding:
            raise KeyError('Ingredient for named config "%s" not found' % ncfg)
        scaffolding[path].named_configs_to_use.append(cfg_name)


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

    for sc_path, sc in scaffolding.items():
        if sc_path:
            sc.logger = root_logger.getChild(sc_path)
        else:
            sc.logger = root_logger

    return root_logger.getChild(experiment.name)


def create_scaffolding(experiment):
    sorted_ingredients = gather_ingredients_topological(experiment)
    scaffolding = OrderedDict()
    for sm in sorted_ingredients:
        scaffolding[sm] = Scaffold(
            sm.cfgs,
            subrunners=OrderedDict([(scaffolding[m].path, scaffolding[m])
                                    for m in sm.ingredients]),
            path=sm.path if sm != experiment else '',
            captured_functions=sm.captured_functions,
            commands=sm.commands,
            named_configs=sm.named_configs,
            generate_seed=sm.gen_seed)
    return OrderedDict([(sc.path, sc) for sc in scaffolding.values()])


def gather_ingredients_topological(ingredient):
    sub_ingredients = defaultdict(int)
    for sm, depth in ingredient.traverse_ingredients():
        sub_ingredients[sm] = max(sub_ingredients[sm], depth)
    return sorted(sub_ingredients, key=lambda x: -sub_ingredients[x])


ConfigModifications = namedtuple('ConfigModifications',
                                 ['added', 'updated', 'typechanges'])


def get_config_modifications(scaffolding):
    added = set()
    updated = set()
    typechanges = {}
    for sc_path, sc in scaffolding.items():
        mr_add, mr_up, mr_tc = sc.get_config_modifications()
        if mr_add or mr_up or mr_tc:
            updated |= set(iter_prefixes(sc_path))
        added |= {join_paths(sc_path, a) for a in mr_add}
        updated |= {join_paths(sc_path, u) for u in mr_up}
        typechanges.update({join_paths(sc_path, k): v
                            for k, v in mr_tc.items()})
    return ConfigModifications(added, updated, typechanges)


def get_command(scaffolding, command_path):
    path, _, command_name = command_path.rpartition('.')
    if path not in scaffolding:
        raise KeyError('Ingredient for command "%s" not found.' % command_path)

    if command_name in scaffolding[path].commands:
        return scaffolding[path].commands[command_name]
    else:
        if path:
            raise KeyError('Command "%s" not found in ingredient "%s"' %
                           (command_name, path))
        else:
            raise KeyError('Command "%s" not found' % command_name)


def create_run(experiment, command_name, config_updates=None, log_level=None,
               named_configs=()):
    scaffolding = create_scaffolding(experiment)
    logger = initialize_logging(experiment, scaffolding, log_level)

    distribute_config_updates(scaffolding, config_updates)
    distribute_named_configs(scaffolding, named_configs)

    for sc in reversed(list(scaffolding.values())):
        sc.set_up_seed()  # partially recursive

    for sc in scaffolding.values():
        sc.set_up_config()

    config = get_configuration(scaffolding)

    config_modifications = get_config_modifications(scaffolding)

    # only get experiment and host info if there are observers
    if experiment.observers:
        experiment_info = experiment.get_info()
        host_info = get_host_info()
    else:
        experiment_info = host_info = dict()

    main_function = get_command(scaffolding, command_name)

    run = Run(config, config_modifications, main_function, experiment.observers,
              logger, experiment.name, experiment_info, host_info)

    for sc in scaffolding.values():
        sc.finalize_initialization(run=run)

    return run