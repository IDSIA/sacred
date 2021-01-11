#!/usr/bin/env python
# coding=utf-8

import os
from collections import OrderedDict, defaultdict
from copy import copy, deepcopy

from sacred.config import (
    ConfigDict,
    chain_evaluate_config_scopes,
    dogmatize,
    load_config_file,
    undogmatize,
)
from sacred.config.config_summary import ConfigSummary
from sacred.config.custom_containers import make_read_only
from sacred.host_info import get_host_info
from sacred.randomness import create_rnd, get_seed
from sacred.run import Run
from sacred.utils import (
    convert_to_nested_dict,
    create_basic_stream_logger,
    get_by_dotted_path,
    is_prefix,
    rel_path,
    iterate_flattened,
    set_by_dotted_path,
    recursive_update,
    iter_prefixes,
    join_paths,
    NamedConfigNotFoundError,
    ConfigAddedError,
)
from sacred.settings import SETTINGS


class Scaffold:
    def __init__(
        self,
        config_scopes,
        subrunners,
        path,
        captured_functions,
        commands,
        named_configs,
        config_hooks,
        generate_seed,
    ):
        self.config_scopes = config_scopes
        self.named_configs = named_configs
        self.subrunners = subrunners
        self.path = path
        self.generate_seed = generate_seed
        self.config_hooks = config_hooks
        self.config_updates = {}
        self.named_configs_to_use = []
        self.config = {}
        self.fallback = None
        self.presets = {}
        self.fixture = None  # TODO: rename
        self.logger = None
        self.seed = None
        self.rnd = None
        self._captured_functions = captured_functions
        self.commands = commands
        self.config_mods = None
        self.summaries = []
        self.captured_args = {
            join_paths(cf.prefix, n)
            for cf in self._captured_functions
            for n in cf.signature.arguments
        }
        self.captured_args.add("__doc__")  # allow setting the config docstring

    def set_up_seed(self, rnd=None):
        if self.seed is not None:
            return

        self.seed = self.config.get("seed")
        if self.seed is None:
            self.seed = get_seed(rnd)

        self.rnd = create_rnd(self.seed)

        if self.generate_seed:
            self.config["seed"] = self.seed

        if "seed" in self.config and "seed" in self.config_mods.added:
            self.config_mods.modified.add("seed")
            self.config_mods.added -= {"seed"}

        # Hierarchically set the seed of proper subrunners
        for subrunner_path, subrunner in reversed(list(self.subrunners.items())):
            if is_prefix(self.path, subrunner_path):
                subrunner.set_up_seed(self.rnd)

    def gather_fallbacks(self):
        fallback = {"_log": self.logger}
        for sr_path, subrunner in self.subrunners.items():
            if self.path and is_prefix(self.path, sr_path):
                path = sr_path[len(self.path) :].strip(".")
                set_by_dotted_path(fallback, path, subrunner.config)
            else:
                set_by_dotted_path(fallback, sr_path, subrunner.config)

        # dogmatize to make the subrunner configurations read-only
        self.fallback = dogmatize(fallback)
        self.fallback.revelation()

    def run_named_config(self, config_name):
        if os.path.isfile(config_name):
            nc = ConfigDict(load_config_file(config_name))
        else:
            if config_name not in self.named_configs:
                raise NamedConfigNotFoundError(
                    named_config=config_name,
                    available_named_configs=tuple(self.named_configs.keys()),
                )
            nc = self.named_configs[config_name]

        cfg = nc(
            fixed=self.get_config_updates_recursive(),
            preset=self.presets,
            fallback=self.fallback,
        )

        return undogmatize(cfg)

    def set_up_config(self):
        self.config, self.summaries = chain_evaluate_config_scopes(
            self.config_scopes,
            fixed=self.config_updates,
            preset=self.config,
            fallback=self.fallback,
        )

        self.get_config_modifications()

    def run_config_hooks(self, config, command_name, logger):
        final_cfg_updates = {}
        for ch in self.config_hooks:
            cfg_upup = ch(deepcopy(config), command_name, logger)
            if cfg_upup:
                recursive_update(final_cfg_updates, cfg_upup)
        recursive_update(final_cfg_updates, self.config_updates)
        return final_cfg_updates

    def get_config_modifications(self):
        self.config_mods = ConfigSummary(
            added={key for key, value in iterate_flattened(self.config_updates)}
        )
        for cfg_summary in self.summaries:
            self.config_mods.update_from(cfg_summary)

    def get_config_updates_recursive(self):
        config_updates = self.config_updates.copy()
        for sr_path, subrunner in self.subrunners.items():
            if not is_prefix(self.path, sr_path):
                continue
            update = subrunner.get_config_updates_recursive()
            if update:
                config_updates[rel_path(self.path, sr_path)] = update
        return config_updates

    def get_fixture(self):
        if self.fixture is not None:
            return self.fixture

        def get_fixture_recursive(runner):
            for sr_path, subrunner in runner.subrunners.items():
                # I am not sure if it is necessary to trigger all
                subrunner.get_fixture()
                get_fixture_recursive(subrunner)
                sub_fix = copy(subrunner.config)
                sub_path = sr_path
                if is_prefix(self.path, sub_path):
                    sub_path = sr_path[len(self.path) :].strip(".")
                # Note: This might fail if we allow non-dict fixtures
                set_by_dotted_path(self.fixture, sub_path, sub_fix)

        self.fixture = copy(self.config)
        get_fixture_recursive(self)

        return self.fixture

    def finalize_initialization(self, run):
        # look at seed again, because it might have changed during the
        # configuration process
        if "seed" in self.config:
            self.seed = self.config["seed"]
        self.rnd = create_rnd(self.seed)

        for cfunc in self._captured_functions:
            # Setup the captured function
            cfunc.logger = self.logger.getChild(cfunc.__name__)
            seed = get_seed(self.rnd)
            cfunc.rnd = create_rnd(seed)
            cfunc.run = run
            cfunc.config = get_by_dotted_path(
                self.get_fixture(), cfunc.prefix, default={}
            )

            # Make configuration read only if enabled in settings
            if SETTINGS.CONFIG.READ_ONLY_CONFIG:
                cfunc.config = make_read_only(cfunc.config)

        if not run.force:
            self._warn_about_suspicious_changes()

    def _warn_about_suspicious_changes(self):
        for add in sorted(self.config_mods.added):
            if not set(iter_prefixes(add)).intersection(self.captured_args):
                if self.path:
                    add = join_paths(self.path, add)
                raise ConfigAddedError(add, config=self.config)
            else:
                self.logger.warning('Added new config entry: "%s"' % add)

        for key, (type_old, type_new) in self.config_mods.typechanged.items():
            if type_old in (int, float) and type_new in (int, float):
                continue
            self.logger.warning(
                'Changed type of config entry "%s" from %s to %s'
                % (key, type_old.__name__, type_new.__name__)
            )

        for cfg_summary in self.summaries:
            for key in cfg_summary.ignored_fallbacks:
                self.logger.warning(
                    'Ignored attempt to set value of "%s", because it is an '
                    "ingredient." % key
                )

    def __repr__(self):
        return "<Scaffold: '{}'>".format(self.path)


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
            scaffolding[""].use_named_config(ncfg)
        else:
            path, _, cfg_name = ncfg.rpartition(".")
            if path not in scaffolding:
                raise KeyError(
                    'Ingredient for named config "{}" not found'.format(ncfg)
                )
            scaffolding[path].use_named_config(cfg_name)


def initialize_logging(experiment, scaffolding, log_level=None):
    if experiment.logger is None:
        root_logger = create_basic_stream_logger()
    else:
        root_logger = experiment.logger

    for sc_path, scaffold in scaffolding.items():
        if sc_path:
            scaffold.logger = root_logger.getChild(sc_path)
        else:
            scaffold.logger = root_logger

    # set log level
    if log_level is not None:
        try:
            lvl = int(log_level)
        except ValueError:
            lvl = log_level
        root_logger.setLevel(lvl)

    return root_logger, root_logger.getChild(experiment.path)


def create_scaffolding(experiment, sorted_ingredients):
    scaffolding = OrderedDict()
    for ingredient in sorted_ingredients[:-1]:
        scaffolding[ingredient] = Scaffold(
            config_scopes=ingredient.configurations,
            subrunners=OrderedDict(
                [(scaffolding[m].path, scaffolding[m]) for m in ingredient.ingredients]
            ),
            path=ingredient.path,
            captured_functions=ingredient.captured_functions,
            commands=ingredient.commands,
            named_configs=ingredient.named_configs,
            config_hooks=ingredient.config_hooks,
            generate_seed=False,
        )

    scaffolding[experiment] = Scaffold(
        experiment.configurations,
        subrunners=OrderedDict(
            [(scaffolding[m].path, scaffolding[m]) for m in experiment.ingredients]
        ),
        path="",
        captured_functions=experiment.captured_functions,
        commands=experiment.commands,
        named_configs=experiment.named_configs,
        config_hooks=experiment.config_hooks,
        generate_seed=True,
    )

    scaffolding_ret = OrderedDict([(sc.path, sc) for sc in scaffolding.values()])
    if len(scaffolding_ret) != len(scaffolding):
        raise ValueError(
            "The pathes of the ingredients are not unique. "
            "{}".format([s.path for s in scaffolding])
        )

    return scaffolding_ret


def gather_ingredients_topological(ingredient):
    sub_ingredients = defaultdict(int)
    for sub_ing, depth in ingredient.traverse_ingredients():
        sub_ingredients[sub_ing] = max(sub_ingredients[sub_ing], depth)
    return sorted(sub_ingredients, key=lambda x: -sub_ingredients[x])


def get_config_modifications(scaffolding):
    config_modifications = ConfigSummary()
    for sc_path, scaffold in scaffolding.items():
        config_modifications.update_add(scaffold.config_mods, path=sc_path)
    return config_modifications


def get_command(scaffolding, command_path):
    path, _, command_name = command_path.rpartition(".")
    if path not in scaffolding:
        raise KeyError('Ingredient for command "%s" not found.' % command_path)

    if command_name in scaffolding[path].commands:
        return scaffolding[path].commands[command_name]
    else:
        if path:
            raise KeyError(
                'Command "%s" not found in ingredient "%s"' % (command_name, path)
            )
        else:
            raise KeyError('Command "%s" not found' % command_name)


def find_best_match(path, prefixes):
    """Find the Ingredient that shares the longest prefix with path."""
    path_parts = path.split(".")
    for p in prefixes:
        if len(p) <= len(path_parts) and p == path_parts[: len(p)]:
            return ".".join(p), ".".join(path_parts[len(p) :])
    return "", path


def distribute_presets(sc_path, prefixes, scaffolding, config_updates):
    for path, value in iterate_flattened(config_updates):
        if sc_path:
            path = sc_path + "." + path
        scaffold_name, suffix = find_best_match(path, prefixes)
        scaff = scaffolding[scaffold_name]
        set_by_dotted_path(scaff.presets, suffix, value)


def distribute_config_updates(prefixes, scaffolding, config_updates):
    for path, value in iterate_flattened(config_updates):
        scaffold_name, suffix = find_best_match(path, prefixes)
        scaff = scaffolding[scaffold_name]
        set_by_dotted_path(scaff.config_updates, suffix, value)


def get_scaffolding_and_config_name(named_config, scaffolding):
    if os.path.exists(named_config):
        path, cfg_name = "", named_config
    else:
        path, _, cfg_name = named_config.rpartition(".")

        if path not in scaffolding:
            raise KeyError(
                'Ingredient for named config "{}" not found'.format(named_config)
            )
    scaff = scaffolding[path]
    return scaff, cfg_name


def create_run(
    experiment,
    command_name,
    config_updates=None,
    named_configs=(),
    force=False,
    log_level=None,
):

    sorted_ingredients = gather_ingredients_topological(experiment)
    scaffolding = create_scaffolding(experiment, sorted_ingredients)
    # get all split non-empty prefixes sorted from deepest to shallowest
    prefixes = sorted(
        [s.split(".") for s in scaffolding if s != ""],
        reverse=True,
        key=lambda p: len(p),
    )

    # --------- configuration process -------------------

    # Phase 1: Config updates
    config_updates = config_updates or {}
    config_updates = convert_to_nested_dict(config_updates)
    root_logger, run_logger = initialize_logging(experiment, scaffolding, log_level)
    distribute_config_updates(prefixes, scaffolding, config_updates)

    # Phase 2: Named Configs
    for ncfg in named_configs:
        scaff, cfg_name = get_scaffolding_and_config_name(ncfg, scaffolding)
        scaff.gather_fallbacks()
        ncfg_updates = scaff.run_named_config(cfg_name)
        distribute_presets(scaff.path, prefixes, scaffolding, ncfg_updates)
        for ncfg_key, value in iterate_flattened(ncfg_updates):
            set_by_dotted_path(config_updates, join_paths(scaff.path, ncfg_key), value)

    distribute_config_updates(prefixes, scaffolding, config_updates)

    # Phase 3: Normal config scopes
    for scaffold in scaffolding.values():
        scaffold.gather_fallbacks()
        scaffold.set_up_config()

        # update global config
        config = get_configuration(scaffolding)
        # run config hooks
        config_hook_updates = scaffold.run_config_hooks(
            config, command_name, run_logger
        )
        recursive_update(scaffold.config, config_hook_updates)

    # Phase 4: finalize seeding
    for scaffold in reversed(list(scaffolding.values())):
        scaffold.set_up_seed()  # partially recursive

    config = get_configuration(scaffolding)
    config_modifications = get_config_modifications(scaffolding)

    # ----------------------------------------------------

    experiment_info = experiment.get_experiment_info()
    host_info = get_host_info(experiment.additional_host_info)
    main_function = get_command(scaffolding, command_name)
    pre_runs = [pr for ing in sorted_ingredients for pr in ing.pre_run_hooks]
    post_runs = [pr for ing in sorted_ingredients for pr in ing.post_run_hooks]

    run = Run(
        config,
        config_modifications,
        main_function,
        copy(experiment.observers),
        root_logger,
        run_logger,
        experiment_info,
        host_info,
        pre_runs,
        post_runs,
        experiment.captured_out_filter,
    )

    if hasattr(main_function, "unobserved"):
        run.unobserved = main_function.unobserved

    run.force = force

    for scaffold in scaffolding.values():
        scaffold.finalize_initialization(run=run)

    return run
