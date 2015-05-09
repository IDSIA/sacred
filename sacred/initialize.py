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
                          iterate_flattened, set_by_dotted_path,
                          recursive_update)

__sacred__ = True  # marks files that should be filtered from stack traces


class Scaffold(object):
    def __init__(self, config_scopes, subrunners, path, captured_functions,
                 commands, named_configs, config_hooks, generate_seed):
        self.config_scopes = config_scopes
        self.named_configs = named_configs
        self.subrunners = subrunners
        self.path = path
        self.generate_seed = generate_seed
        self.config_hooks = config_hooks
        self.config_updates = {}
        self.named_configs_to_use = []
        self.config = None
        self.fallback = None
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

    def pick_relevant_config_updates(self, config_updates, past_paths):
        if config_updates is None:
            return

        for path, value in iterate_flattened(config_updates):
            for prefix, suffix in reversed(list(iter_path_splits(path))):
                if prefix in past_paths:
                    # don't use config_updates for prior ingredients
                    break
                elif prefix == self.path:
                    set_by_dotted_path(self.config_updates, suffix, value)
                    break

    def gather_fallbacks(self):
        fallback = {}
        for sr_path, subrunner in self.subrunners.items():
            if self.path and is_prefix(self.path, sr_path):
                path = sr_path[len(self.path):].strip('.')
                set_by_dotted_path(fallback, path, subrunner.config)
            else:
                set_by_dotted_path(fallback, sr_path, subrunner.config)

        # dogmatize to make the subrunner configurations read-only
        self.fallback = dogmatize(fallback)
        self.fallback.revelation()

    def use_named_config(self, config_name):
        if os.path.exists(config_name):
            self.named_configs_to_use.append(ConfigDict(load_config_file(config_name)))
        else:
            self.named_configs_to_use.append(self.named_configs[config_name])

    def set_up_config(self):
        # named configs go first
        self.config_updates, _ = chain_evaluate_config_scopes(
            self.named_configs_to_use,
            fixed=self.config_updates,
            preset={},
            fallback=self.fallback)

        # unnamed (default) configs second
        self.config, self.summaries = chain_evaluate_config_scopes(
            self.config_scopes,
            fixed=self.config_updates,
            preset=self.config,
            fallback=self.fallback)

        self.get_config_modifications()

    def run_config_hooks(self, config, config_updates):
        cfg_upup, _ = chain_evaluate_config_scopes(
            self.config_hooks,
            fixed=config_updates,
            preset={},
            fallback=config)
        
        print('additional config_updates:', cfg_upup)

        return cfg_upup

    def get_config_modifications(self):
        self.config_mods = ConfigSummary()
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
        if not scaffold.config:
            continue
        if sc_path:
            set_by_dotted_path(config, sc_path, scaffold.config)
        else:
            config.update(scaffold.config)
    return config


def distribute_named_configs(scaffolding, named_configs):
    for ncfg in named_configs:
        if os.path.exists(ncfg):
            scaffolding[''].use_named_config(ncfg)
        else:
            path, _, cfg_name = ncfg.rpartition('.')
            if path not in scaffolding:
                raise KeyError('Ingredient for named config "{}" not found'
                               .format(ncfg))
            scaffolding[path].use_named_config(cfg_name)


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

    return root_logger.getChild(experiment.name)


def create_scaffolding(experiment, sorted_ingredients):
    scaffolding = OrderedDict()
    for ingredient in sorted_ingredients:
        scaffolding[ingredient] = Scaffold(
            config_scopes=ingredient.cfgs,
            subrunners=OrderedDict([(scaffolding[m].path, scaffolding[m])
                                    for m in ingredient.ingredients]),
            path=ingredient.path if ingredient != experiment else '',
            captured_functions=ingredient.captured_functions,
            commands=ingredient.commands,
            named_configs=ingredient.named_configs,
            config_hooks=ingredient.config_hooks,
            generate_seed=ingredient.gen_seed)
    return OrderedDict([(sc.path, sc) for sc in scaffolding.values()])


def gather_ingredients_topological(ingredient):
    sub_ingredients = defaultdict(int)
    for ingredient, depth in ingredient._traverse_ingredients():
        sub_ingredients[ingredient] = max(sub_ingredients[ingredient], depth)
    return sorted(sub_ingredients, key=lambda x: -sub_ingredients[x])


def get_config_modifications(scaffolding):
    config_modifications = ConfigSummary()
    for sc_path, scaffold in scaffolding.items():
        config_modifications.update_from(scaffold.config_mods, path=sc_path)
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


def execute_pre_runs(ingredients, command_name, config_updates, named_configs):
    args = (command_name, config_updates, named_configs)
    for ingred in ingredients:
        if ingred._pre_run:
            args = ingred._pre_run(*args)
    return args


def create_run(experiment, command_name, config_updates=None, log_level=None,
               named_configs=()):

    sorted_ingredients = gather_ingredients_topological(experiment)
    scaffolding = create_scaffolding(experiment, sorted_ingredients)

    # --------- configuration process -------------------
    distribute_named_configs(scaffolding, named_configs)
    config_updates = config_updates or {}
    config_updates = convert_to_nested_dict(config_updates)

    past_paths = set()
    for scaffold in scaffolding.values():
        scaffold.pick_relevant_config_updates(config_updates, past_paths)
        past_paths.add(scaffold.path)
        scaffold.gather_fallbacks()
        scaffold.set_up_config()

        # update global config
        config = get_configuration(scaffolding)
        # run config hooks
        config_updates_update = scaffold.run_config_hooks(config, config_updates)
        recursive_update(config_updates, config_updates_update)

    for scaffold in reversed(list(scaffolding.values())):
        scaffold.set_up_seed()  # partially recursive

    config = get_configuration(scaffolding)
    config_modifications = get_config_modifications(scaffolding)

    # ----------------------------------------------------

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
