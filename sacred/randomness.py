#!/usr/bin/env python
# coding=utf-8

import random

import sacred.optional as opt
from sacred.utils import module_is_in_cache

SEEDRANGE = (1, int(1e9))


def get_seed(rnd=None):
    if rnd is None:
        return random.randint(*SEEDRANGE)
    return rnd.randint(*SEEDRANGE)


def create_rnd(seed):
    assert isinstance(seed, int), "Seed has to be integer but was {} {}".format(
        repr(seed), type(seed)
    )
    if opt.has_numpy:
        return opt.np.random.RandomState(seed)
    else:
        return random.Random(seed)


def set_global_seed(seed):
    set_python_random_seed(seed)
    if opt.has_numpy:
        set_numpy_seed(seed)
    if module_is_in_cache("tensorflow"):
        set_tensorflow_seed(seed)
    if module_is_in_cache("torch"):
        set_pytorch_seed(seed)


def set_python_random_seed(seed):
    random.seed(seed)


def set_numpy_seed(seed):
    import numpy as np

    np.random.seed(seed)


def set_tensorflow_seed(seed):
    tf = opt.get_tensorflow()
    tf.set_random_seed(seed)


def set_pytorch_seed(seed):
    import torch

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
