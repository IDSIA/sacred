#!/usr/bin/env python
# coding=utf-8

import random

import sacred.optional as opt
from sacred.utils import module_is_in_cache


def create_rng(seed):
    assert isinstance(seed, int), "Seed has to be integer but was {} {}".format(
        repr(seed), type(seed)
    )
    if opt.has_numpy:
        try:
            seed_sequence = opt.np.random.SeedSequence(seed)
            return opt.np.random.default_rng(seed_sequence.spawn(1)[0])
        except Exception:
            return opt.np.random.RandomState(seed)
    else:
        return random.Random(seed)


def set_global_seed(seed):
    random.seed(seed)
    if opt.has_numpy:
        try:
            opt.np.random.seed(seed)
        except Exception:
            pass
    if module_is_in_cache("tensorflow"):
        tf = opt.get_tensorflow()
        tf.set_random_seed(seed)
    if module_is_in_cache("torch"):
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)


class SeedGenerator:
    def __init__(self, seed=None, min=1, max=1e9):
        self.min = min
        self.max = max
        self.rng = random.Random(seed)

    def __iter__(self):
        return self

    def __next__(self):
        return self.rng.randint(self.min, self.max)
