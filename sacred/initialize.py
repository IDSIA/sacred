#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import os
from collections import OrderedDict, defaultdict
from copy import copy

from sacred.config import (ConfigDict, chain_evaluate_config_scopes, dogmatize,
                           load_config_file)
from sacred.config.config_summary import ConfigSummary
from sacred.host_info import get_host_info
from sacred.randomness import create_rnd, get_seed
from sacred.run import Run
from sacred.utils import (convert_to_nested_dict, create_basic_stream_logger,
                          get_by_dotted_path, is_prefix, iter_path_splits,
                          iterate_flattened, set_by_dotted_path)

__sacred__ = True  # marks files that should be filtered from stack traces


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
        self.config_mods = None
        self.summaries = []

    def set_up_seed(self, rnd=None):
        if self.seed is not None:
            return

        self.seed = self.config.get('seed') or get_seed(rnd)
        self.rnd = create_rnd(self.seed)

        if self.generate_seed:
            self.config['seed'] = self.seed

        if 'seed' in self.config and 'seed' in self.config_mods.added:
            self.config_mods.modified.add('seed')
            self.config_mods.added -= {'seed'}

        # Hierarchically set the seed of proper subrunners
        for subrunner_path, subrunner in reversed(list(
                self.subrunners.items())):
            if is_prefix(self.path, subrunner_path):
                subrunner.set_up_seed(self.rnd)

    def set_up_config(self):
        if self.config is not None:
            return self.config

        # gather presets
        fallback = {}
        for sr_path, subrunner in self.subrunners.items():
            if self.path and is_prefix(self.path, sr_path):
                path = sr_path[len(self.path):].strip('.')
                set_by_dotted_path(fallback, path, subrunner.config)
            else:
                set_by_dotted_path(fallback, sr_path, subrunner.config)

        # dogmatize to make the subrunner configurations read-only
        const_fallback = dogmatize(fallback)
        const_fallback.revelation()

        self.config = {}

        # named configs first
        cfg_list = []
        for ncfg in self.named_configs_to_use:
            if os.path.exists(ncfg):
                cfg_list.append(ConfigDict(load_config_file(ncfg)))
            else:
                cfg_list.append(self.named_configs[ncfg])

        self.config_updates, _ = chain_evaluate_config_scopes(
            cfg_list,
            fixed=self.config_updates,
            preset=self.config,
            fallback=const_fallback)

        # unnamed (default) configs second
        self.config, self.summaries = chain_evaluate_config_scopes(
            self.config_scopes,
            fixed=self.config_updates,
            preset=self.config,
            fallback=const_fallback)

        self.get_config_modifications()

    def get_config_modifications(self):
        self.config_mods = ConfigSummary(
            added={key
                   for key, value in iterate_flattened(self.config_updates)})
        for cfg_summary in self.summaries:
            self.config_mods.update_from(cfg_summary)

    def get_fixture(self):
        if self.fixture is not None:
            return self.fixture

        self.fixture = copy(self.config)
        for sr_path, subrunner in self.subrunners.items():
            sub_fix = subrunner.get_fixture()
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

        for cfunc in self._captured_functions:
            cfunc.logger = self.logger.getChild(cfunc.__name__)
            cfunc.config = get_by_dotted_path(self.get_fixture(), cfunc.prefix)
            seed = get_seed(self.rnd)
            cfunc.rnd = create_rnd(seed)
            cfunc.run = run

        self._warn_about_suspicious_changes()

    def _warn_about_suspicious_changes(self):
        for add in sorted(self.config_mods.added):
            self.logger.warning('Added new config entry: "%s"' % add)

        for key, (type_old, type_new) in self.config_mods.typechanged.items():
            if (isinstance(type_old, type(None)) or
                    (type_old in (int, float) and type_new in (int, float))):
                continue
            self.logger.warning(
                'Changed type of config entry "%s" from %s to %s' %
                (key, type_old.__name__, type_new.__name__))

        for cfg_summary in self.summaries:
            for key in cfg_summary.ignored_fallbacks:
                self.logger.warning(
                    'Ignored attempt to set value of "%s", because it is an '
                    'ingredient.' % key
                )


def get_configuration(scaffolding):
    config = {}
    for sc_path, scaffold in reversed(list(scaffolding.items())):
        if sc_path:
            set_by_dotted_path(config, sc_path, scaffold.config)
        else:
            config.update(scaffold.config)
    return config


def distribute_config_updates(scaffolding, config_updates):
    if config_updates is None:
        return
    nested_config_updates = convert_to_nested_dict(config_updates)
    for path, value in iterate_flattened(nested_config_updates):
        for prefix, suffix in reversed(list(iter_path_splits(path))):
            if prefix in scaffolding:
                set_by_dotted_path(scaffolding[prefix].config_updates, suffix,
                                   value)
                break
                # this is guaranteed to occur for one of the modrunners,
                # because the exrunner has path ''


def distribute_named_configs(scaffolding, named_configs):
    for ncfg in named_configs:
        if os.path.exists(ncfg):
            scaffolding[''].named_configs_to_use.append(ncfg)
        else:
            path, _, cfg_name = ncfg.rpartition('.')
            if path not in scaffolding:
                raise KeyError('Ingredient for named config "{}" not found'
                               .format(ncfg))
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

    for sc_path, scaffold in scaffolding.items():
        if sc_path:
            scaffold.logger = root_logger.getChild(sc_path)
        else:
            scaffold.logger = root_logger

    return root_logger.getChild(experiment.path)


def create_scaffolding(experiment):
    sorted_ingredients = gather_ingredients_topological(experiment)
    scaffolding = OrderedDict()
    for ingredient in sorted_ingredients[:-1]:
        scaffolding[ingredient] = Scaffold(
            ingredient.cfgs,
            subrunners=OrderedDict([(scaffolding[m].path, scaffolding[m])
                                    for m in ingredient.ingredients]),
            path=ingredient.path if ingredient != experiment else '',
            captured_functions=ingredient.captured_functions,
            commands=ingredient.commands,
            named_configs=ingredient.named_configs,
            generate_seed=False)

    scaffolding[experiment] = Scaffold(
        experiment.cfgs,
        subrunners=OrderedDict([(scaffolding[m].path, scaffolding[m])
                                for m in experiment.ingredients]),
        path=experiment.path if experiment != experiment else '',
        captured_functions=experiment.captured_functions,
        commands=experiment.commands,
        named_configs=experiment.named_configs,
        generate_seed=True)
    return OrderedDict([(sc.path, sc) for sc in scaffolding.values()])


def gather_ingredients_topological(ingredient):
    sub_ingredients = defaultdict(int)
    for sub_ing, depth in ingredient._traverse_ingredients():
        sub_ingredients[sub_ing] = max(sub_ingredients[sub_ing], depth)
    return sorted(sub_ingredients, key=lambda x: -sub_ingredients[x])


def get_config_modifications(scaffolding, config_updates):
    config_modifications = ConfigSummary()
    for sc_path, scaffold in scaffolding.items():
        config_modifications.update_add(scaffold.config_mods, path=sc_path)
    return config_modifications


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

    distribute_config_updates(scaffolding, config_updates)
    distribute_named_configs(scaffolding, named_configs)

    for scaffold in scaffolding.values():
        scaffold.set_up_config()

    for scaffold in reversed(list(scaffolding.values())):
        scaffold.set_up_seed()  # partially recursive

    config = get_configuration(scaffolding)
    config_modifications = get_config_modifications(scaffolding,
                                                    config_updates)

    experiment_info = experiment.get_experiment_info()
    host_info = get_host_info()
    main_function = get_command(scaffolding, command_name)

    logger = initialize_logging(experiment, scaffolding, log_level)
    run = Run(config, config_modifications, main_function,
              experiment.observers, logger, experiment_info,
              host_info)

    for scaffold in scaffolding.values():
        scaffold.finalize_initialization(run=run)

    return run
