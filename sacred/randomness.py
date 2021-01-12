#!/usr/bin/env python
# coding=utf-8

import random

import sacred.optional as opt
from sacred.settings import SETTINGS
from sacred.utils import module_is_in_cache

SEEDRANGE = (1, int(1e9))


def get_seed(rnd=None):
    if rnd is None:
        return random.randint(*SEEDRANGE)
    else:
        try:
            return rnd.integers(*SEEDRANGE, dtype=int)
        except Exception:
            return rnd.randint(*SEEDRANGE)


def create_rnd(seed):
    assert isinstance(seed, int), "Seed has to be integer but was {} {}".format(
        repr(seed), type(seed)
    )
    if opt.has_numpy:
        if SETTINGS.CONFIG.NUMPY_RANDOM_LEGACY_API:
            return opt.np.random.RandomState(seed)
        else:
            return opt.np.random.default_rng(seed)
    else:
        return random.Random(seed)


def set_global_seed(seed):
    random.seed(seed)
    if opt.has_numpy:
        opt.np.random.seed(seed)
    if module_is_in_cache("tensorflow"):
        tf = opt.get_tensorflow()
        tf.set_random_seed(seed)
    if module_is_in_cache("torch"):
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
